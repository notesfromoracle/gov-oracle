from .bangladesh import BANGLADESH
from .registry import COUNTRIES

ALL_GOVERNMENTS: list[dict] = [BANGLADESH, *COUNTRIES]

REGISTRY: dict[str, dict] = {
    alias: government
    for government in ALL_GOVERNMENTS
    for alias in government["aliases"]
}


def lookup(government_name: str) -> dict | None:
    return REGISTRY.get(government_name.strip().lower())


__all__ = ["ALL_GOVERNMENTS", "BANGLADESH", "COUNTRIES", "REGISTRY", "lookup"]
