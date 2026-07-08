"""Validation of the multi-country registry."""
from __future__ import annotations

from gov_oracle_agents.seeds import ALL_GOVERNMENTS, REGISTRY, lookup

REQUIRED_INSTITUTION_TYPES = {"ministry", "parliament", "audit", "statistics", "central_bank", "procurement"}


def test_registry_has_a_broad_mixture():
    assert len(ALL_GOVERNMENTS) >= 21
    codes = [g["country_code"] for g in ALL_GOVERNMENTS]
    assert len(codes) == len(set(codes)), "country codes must be unique"
    names = [g["government_name"] for g in ALL_GOVERNMENTS]
    assert len(names) == len(set(names)), "canonical names must be unique"
    # mixture: high-income and lower-income economies both present
    assert {"US", "GB", "DE", "JP", "NO"} <= set(codes)
    assert {"BD", "ET", "NP", "KE", "NG"} <= set(codes)


def test_every_government_is_complete():
    for gov in ALL_GOVERNMENTS:
        assert gov["jurisdiction_type"] == "national"
        assert gov["description"]
        assert len(gov["institutions"]) >= 6, gov["government_name"]
        assert len(gov["sources"]) >= 7, gov["government_name"]
        types = {inst["institution_type"] for inst in gov["institutions"]}
        assert REQUIRED_INSTITUTION_TYPES <= types, (
            f"{gov['government_name']} missing institution pillars: "
            f"{REQUIRED_INSTITUTION_TYPES - types}"
        )
        for source in gov["sources"]:
            assert source["url"].startswith(("http://", "https://")), source
            assert 0.0 < source["reliability_score"] <= 1.0
        # every government must monitor at least one non-official source
        assert any(s["source_type"] == "news" for s in gov["sources"])
        # and its official pillars
        source_types = {s["source_type"] for s in gov["sources"]}
        assert "procurement" in source_types, gov["government_name"]
        assert "audit" in source_types, gov["government_name"]


def test_resolver_seeds_any_registry_country(settings):
    from gov_oracle_agents.agents import GovernmentResolverAgent, SourceDiscoveryAgent
    from gov_oracle_agents.storage import Institution, init_db, session_scope

    init_db(settings.database_url)
    with session_scope(settings.database_url) as session:
        government = GovernmentResolverAgent().resolve(session, "japan")
        assert government.name == "Government of Japan"
        assert government.country_code == "JP"
        sources = SourceDiscoveryAgent().discover(session, government)
        assert len(sources) >= 7
        institutions = session.query(Institution).filter_by(government_id=government.id).all()
        assert any(i.institution_type == "audit" for i in institutions)

        # a second government coexists without collisions
        kenya = GovernmentResolverAgent().resolve(session, "Republic of Kenya")
        assert kenya.country_code == "KE"
        assert kenya.id != government.id


def test_aliases_resolve_and_do_not_collide():
    alias_total = sum(len(g["aliases"]) for g in ALL_GOVERNMENTS)
    assert len(REGISTRY) == alias_total, "an alias is claimed by two governments"
    assert lookup("United Kingdom")["country_code"] == "GB"
    assert lookup("  government of KENYA ")["country_code"] == "KE"
    assert lookup("usa")["country_code"] == "US"
    assert lookup("Brasil")["country_code"] == "BR"
    assert lookup("Government of Bangladesh")["country_code"] == "BD"
    assert lookup("Atlantis") is None
