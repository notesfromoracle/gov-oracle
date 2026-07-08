"""Fetch layer: httpx first, headless browser as rescue.

Government sites are the worst of the web: bot walls, JS-only shells,
ancient TLS, meta-refresh redirects. The SmartFetcher tries plain HTTP and
falls back to Playwright (Chromium) when the response looks like a blocked
or empty shell. Playwright is optional — without it the fallback is simply
skipped and the failure recorded, which is itself an accessibility signal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import httpx

from ..config import Settings, get_settings

logger = logging.getLogger(__name__)

BLOCK_MARKERS = (
    "just a moment",
    "checking your browser",
    "enable javascript",
    "javascript is required",
    "captcha",
    "access denied",
    "attention required",
)
BLOCKISH_STATUSES = {403, 406, 429, 503}


@dataclass
class FetchResult:
    url: str
    ok: bool
    status_code: int | None = None
    content_type: str = ""
    text: str = ""  # decoded body for text-ish types
    content: bytes = b""  # raw bytes (needed for PDFs)
    error: str | None = None
    via_browser: bool = False
    # Fetched only by ignoring an invalid TLS certificate. Common on
    # government sites with broken chains — an accessibility finding.
    ssl_invalid: bool = False

    @property
    def is_html(self) -> bool:
        return "html" in self.content_type

    @property
    def is_pdf(self) -> bool:
        return "pdf" in self.content_type or self.url.lower().split("?")[0].endswith(".pdf")

    @property
    def is_machine_readable(self) -> bool:
        return any(kind in self.content_type for kind in ("html", "csv", "json", "xml"))


def looks_blocked(result: FetchResult) -> bool:
    """Would a headless browser plausibly do better than this response?"""
    if not result.ok:
        return True
    if result.status_code in BLOCKISH_STATUSES:
        return True
    if result.is_html:
        stripped = _visible_text_size(result.text)
        if stripped < 300:
            return True
        lowered = result.text[:5000].lower()
        if any(marker in lowered for marker in BLOCK_MARKERS):
            return True
    return False


def _visible_text_size(html: str) -> int:
    from ..utils import html_to_text

    return len(html_to_text(html))


class HttpxFetcher:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        client_kwargs = dict(
            timeout=self.settings.crawl_timeout_seconds,
            follow_redirects=True,
            headers={"User-Agent": self.settings.crawl_user_agent},
        )
        self._client = httpx.Client(**client_kwargs)
        # Many government sites serve broken TLS chains (missing
        # intermediates). Auditing them still requires reading them, so on a
        # certificate failure we retry insecurely and FLAG the result — the
        # broken chain feeds the accessibility score instead of hiding the site.
        self._insecure_client = httpx.Client(verify=False, **client_kwargs)

    def fetch(self, url: str) -> FetchResult:
        try:
            response = self._client.get(url)
            ssl_invalid = False
        except Exception as exc:  # noqa: BLE001 — failure type is a finding
            if not _is_tls_failure(exc):
                return FetchResult(url=url, ok=False, error=f"{type(exc).__name__}: {exc}")
            try:
                response = self._insecure_client.get(url)
                ssl_invalid = True
                logger.info("fetched %s despite invalid TLS certificate", url)
            except Exception as retry_exc:  # noqa: BLE001
                return FetchResult(
                    url=url, ok=False, error=f"{type(retry_exc).__name__}: {retry_exc}"
                )
        content_type = response.headers.get("content-type", "").lower()
        is_texty = any(k in content_type for k in ("text", "html", "json", "xml", "csv"))
        return FetchResult(
            url=str(response.url),
            ok=response.status_code < 400,
            status_code=response.status_code,
            content_type=content_type,
            text=response.text if is_texty else "",
            content=response.content,
            error=None if response.status_code < 400 else f"HTTP {response.status_code}",
            ssl_invalid=ssl_invalid,
        )

    def close(self) -> None:
        self._client.close()
        self._insecure_client.close()


def _is_tls_failure(exc: Exception) -> bool:
    text = f"{type(exc).__name__}: {exc}".lower()
    return "ssl" in text or "certificate" in text or "tls" in text


class PlaywrightFetcher:
    """Lazy Chromium instance, shared across the crawl run."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._playwright = None
        self._browser = None

    @staticmethod
    def available() -> bool:
        try:
            import playwright.sync_api  # noqa: F401

            return True
        except ImportError:
            return False

    def _ensure_browser(self):
        if self._browser is None:
            from playwright.sync_api import sync_playwright

            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
        return self._browser

    def fetch(self, url: str) -> FetchResult:
        try:
            browser = self._ensure_browser()
            page = browser.new_page(
                user_agent=self.settings.crawl_user_agent,
                ignore_https_errors=True,  # broken chains are recorded, not fatal
            )
            try:
                response = page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=self.settings.crawl_timeout_seconds * 1000,
                )
                # give JS shells a moment to paint real content
                page.wait_for_timeout(1500)
                html = page.content()
                status = response.status if response else None
                return FetchResult(
                    url=page.url,
                    ok=status is not None and status < 400,
                    status_code=status,
                    content_type="text/html",
                    text=html,
                    content=html.encode("utf-8", errors="replace"),
                    error=None if status and status < 400 else f"HTTP {status}",
                    via_browser=True,
                )
            finally:
                page.close()
        except Exception as exc:  # noqa: BLE001
            return FetchResult(
                url=url, ok=False, error=f"{type(exc).__name__}: {exc}", via_browser=True
            )

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
            self._browser = None
        if self._playwright is not None:
            self._playwright.stop()
            self._playwright = None


class SmartFetcher:
    """httpx first; Playwright rescue when the response looks blocked."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self._http = HttpxFetcher(self.settings)
        self._browser: PlaywrightFetcher | None = None
        self._browser_enabled = (
            self.settings.crawl_use_browser and PlaywrightFetcher.available()
        )

    def fetch(self, url: str) -> FetchResult:
        result = self._http.fetch(url)
        # PDFs and other binaries never need a browser
        if result.ok and not result.is_html:
            return result
        if self._browser_enabled and looks_blocked(result):
            if self._browser is None:
                self._browser = PlaywrightFetcher(self.settings)
            rescued = self._browser.fetch(url)
            if rescued.ok and not looks_blocked(rescued):
                logger.info("browser rescued %s", url)
                return rescued
            # keep whichever attempt got further
            if rescued.ok and not result.ok:
                return rescued
        return result

    def close(self) -> None:
        self._http.close()
        if self._browser is not None:
            self._browser.close()
