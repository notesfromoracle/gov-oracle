"""Government Resolver Agent.

Resolves a free-text government name to a canonical government record with
official domains and major institutions. Known governments come from the
curated registry; unknown ones get a minimal record (extend the registry or
add LLM-assisted resolution as coverage grows).
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..seeds import lookup
from ..storage import Government, Institution


class GovernmentResolverAgent:
    def resolve(
        self,
        session: Session,
        government_name: str,
        country_code: str | None = None,
        jurisdiction_type: str = "national",
    ) -> Government:
        registry = lookup(government_name)
        canonical_name = registry["government_name"] if registry else government_name.strip()

        government = session.scalar(select(Government).where(Government.name == canonical_name))
        if government is None:
            government = Government(
                name=canonical_name,
                country_code=(registry or {}).get("country_code", country_code),
                jurisdiction_type=(registry or {}).get("jurisdiction_type", jurisdiction_type),
                description=(registry or {}).get("description"),
            )
            session.add(government)
            session.flush()

        if registry:
            existing = {
                inst.name
                for inst in session.scalars(
                    select(Institution).where(Institution.government_id == government.id)
                )
            }
            for inst in registry["institutions"]:
                if inst["name"] not in existing:
                    session.add(
                        Institution(
                            government_id=government.id,
                            name=inst["name"],
                            institution_type=inst["institution_type"],
                            website_url=inst.get("website_url"),
                        )
                    )
            session.flush()
        return government
