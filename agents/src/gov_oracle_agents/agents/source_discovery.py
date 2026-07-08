"""Source Discovery Agent.

Registers the known public sources for a government in the database.
For the MVP the source list comes from the curated registry; the agent is
additive and idempotent, so manually added sources are preserved and
re-discovery never duplicates rows.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..seeds import lookup
from ..storage import Government, Institution, Source


class SourceDiscoveryAgent:
    def discover(self, session: Session, government: Government) -> list[Source]:
        registry = lookup(government.name)
        if registry is None:
            return list(
                session.scalars(select(Source).where(Source.government_id == government.id))
            )

        institutions_by_name = {
            inst.name: inst
            for inst in session.scalars(
                select(Institution).where(Institution.government_id == government.id)
            )
        }
        existing_urls = {
            src.url
            for src in session.scalars(
                select(Source).where(Source.government_id == government.id)
            )
        }

        for entry in registry["sources"]:
            if entry["url"] in existing_urls:
                continue
            existing_urls.add(entry["url"])
            institution = institutions_by_name.get(entry.get("institution") or "")
            session.add(
                Source(
                    government_id=government.id,
                    institution_id=institution.id if institution else None,
                    name=entry["name"],
                    url=entry["url"],
                    source_type=entry["source_type"],
                    country_code=government.country_code,
                    reliability_score=entry.get("reliability_score", 0.5),
                    status="active",
                )
            )

        # Institution websites are sources in their own right: ministries
        # publish budgets/reports on their own portals, not the national one.
        for institution in institutions_by_name.values():
            url = (institution.website_url or "").rstrip("/")
            if not url or url in existing_urls:
                continue
            existing_urls.add(url)
            session.add(
                Source(
                    government_id=government.id,
                    institution_id=institution.id,
                    name=f"{institution.name} — official site",
                    url=url,
                    source_type="government",
                    country_code=government.country_code,
                    reliability_score=0.8,
                    status="active",
                )
            )
        session.flush()
        return list(
            session.scalars(select(Source).where(Source.government_id == government.id))
        )
