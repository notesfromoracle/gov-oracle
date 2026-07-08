"""Seed the database with every government in the curated registry.

Usage (from the repo root, with the agents package installed):

    python seed/seed_all.py

Registers each government with its institutions and sources so the frontend
lists all of them immediately. Reports are generated per government by agent
runs (scheduled, API-triggered, or CLI); Bangladesh additionally gets the
bundled sample report so the demo has content out of the box.
"""
from __future__ import annotations

from gov_oracle_agents.agents import GovernmentResolverAgent, SourceDiscoveryAgent
from gov_oracle_agents.seeds import ALL_GOVERNMENTS
from gov_oracle_agents.storage import init_db, session_scope

import seed_bangladesh


def main() -> None:
    init_db()
    with session_scope() as session:
        resolver = GovernmentResolverAgent()
        discovery = SourceDiscoveryAgent()
        for entry in ALL_GOVERNMENTS:
            government = resolver.resolve(session, entry["government_name"])
            sources = discovery.discover(session, government)
            print(f"Seeded {government.name} ({government.country_code}): {len(sources)} sources")

    # Bangladesh sample report (skips itself if reports already exist)
    seed_bangladesh.main()


if __name__ == "__main__":
    main()
