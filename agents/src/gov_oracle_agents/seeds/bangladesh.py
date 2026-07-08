"""Curated registry for the Government of Bangladesh (MVP government).

The Government Resolver and Source Discovery agents consult this registry
first; unknown governments fall back to LLM-assisted resolution. Keeping a
curated registry for the MVP government makes runs reproducible and keeps
the crawler pointed at real, official endpoints.
"""

BANGLADESH = {
    "government_name": "Government of Bangladesh",
    "country_code": "BD",
    "jurisdiction_type": "national",
    "aliases": ["bangladesh", "bd", "government of bangladesh", "gob", "peoples republic of bangladesh"],
    "official_domains": ["bangladesh.gov.bd", "portal.gov.bd"],
    "description": (
        "The Government of the People's Republic of Bangladesh, a unitary "
        "parliamentary republic. National-level public information audit."
    ),
    "institutions": [
        {"name": "Ministry of Finance", "institution_type": "ministry", "website_url": "https://mof.gov.bd"},
        {"name": "Finance Division", "institution_type": "division", "website_url": "https://mof.portal.gov.bd"},
        {"name": "Bangladesh Planning Commission", "institution_type": "planning", "website_url": "https://plancomm.gov.bd"},
        {"name": "Jatiya Sangsad (Parliament)", "institution_type": "parliament", "website_url": "https://www.parliament.gov.bd"},
        {"name": "Bangladesh Public Procurement Authority (BPPA)", "institution_type": "procurement", "website_url": "https://bppa.gov.bd"},
        {"name": "Office of the Comptroller and Auditor General", "institution_type": "audit", "website_url": "https://cag.org.bd"},
        {"name": "Bangladesh Bureau of Statistics", "institution_type": "statistics", "website_url": "https://bbs.gov.bd"},
        {"name": "Bangladesh Bank", "institution_type": "central_bank", "website_url": "https://www.bb.org.bd"},
        {"name": "Bangladesh Election Commission", "institution_type": "election", "website_url": "https://www.ecs.gov.bd"},
        {"name": "Supreme Court of Bangladesh", "institution_type": "judiciary", "website_url": "https://www.supremecourt.gov.bd"},
        {"name": "Ministry of Health and Family Welfare", "institution_type": "ministry", "website_url": "https://mohfw.gov.bd"},
        {"name": "Ministry of Education", "institution_type": "ministry", "website_url": "https://moedu.gov.bd"},
        {"name": "Ministry of Road Transport and Bridges", "institution_type": "ministry", "website_url": "https://rthd.gov.bd"},
        {"name": "Implementation Monitoring and Evaluation Division (IMED)", "institution_type": "monitoring", "website_url": "https://imed.gov.bd"},
        {"name": "National Board of Revenue", "institution_type": "revenue", "website_url": "https://nbr.gov.bd"},
    ],
    "sources": [
        {
            "name": "National Portal of Bangladesh",
            "url": "https://bangladesh.gov.bd",
            "source_type": "government",
            "institution": None,
            "reliability_score": 0.9,
        },
        {
            "name": "Ministry of Finance — Budget publications",
            "url": "https://mof.portal.gov.bd/site/page/28bff2c1-3ecf-42dc-b57e-8724a10d15d3",
            "source_type": "budget",
            "institution": "Finance Division",
            "reliability_score": 0.9,
        },
        {
            "name": "e-GP national procurement portal",
            "url": "https://www.eprocure.gov.bd",
            "source_type": "procurement",
            "institution": "Bangladesh Public Procurement Authority (BPPA)",
            "reliability_score": 0.85,
        },
        {
            "name": "BPPA — Bangladesh Public Procurement Authority",
            "url": "https://bppa.gov.bd",
            "source_type": "procurement",
            "institution": "Bangladesh Public Procurement Authority (BPPA)",
            "reliability_score": 0.85,
        },
        {
            "name": "Bangladesh Planning Commission",
            "url": "https://plancomm.gov.bd",
            "source_type": "planning",
            "institution": "Bangladesh Planning Commission",
            "reliability_score": 0.85,
        },
        {
            "name": "Bangladesh Bureau of Statistics",
            "url": "https://bbs.gov.bd",
            "source_type": "statistics",
            "institution": "Bangladesh Bureau of Statistics",
            "reliability_score": 0.9,
        },
        {
            "name": "Office of the Comptroller and Auditor General — audit reports",
            "url": "https://cag.org.bd",
            "source_type": "audit",
            "institution": "Office of the Comptroller and Auditor General",
            "reliability_score": 0.9,
        },
        {
            "name": "Jatiya Sangsad — Parliament of Bangladesh",
            "url": "https://www.parliament.gov.bd",
            "source_type": "parliament",
            "institution": "Jatiya Sangsad (Parliament)",
            "reliability_score": 0.9,
        },
        {
            "name": "Bangladesh Bank — central bank publications",
            "url": "https://www.bb.org.bd",
            "source_type": "central_bank",
            "institution": "Bangladesh Bank",
            "reliability_score": 0.9,
        },
        {
            "name": "Laws of Bangladesh (bdlaws)",
            "url": "http://bdlaws.minlaw.gov.bd",
            "source_type": "legal",
            "institution": None,
            "reliability_score": 0.85,
        },
        {
            "name": "IMED — project implementation monitoring",
            "url": "https://imed.gov.bd",
            "source_type": "monitoring",
            "institution": "Implementation Monitoring and Evaluation Division (IMED)",
            "reliability_score": 0.8,
        },
        {
            "name": "Press Information Department",
            "url": "https://pressinform.gov.bd",
            "source_type": "press",
            "institution": None,
            "reliability_score": 0.75,
        },
        {
            "name": "The Daily Star — national news",
            "url": "https://www.thedailystar.net",
            "source_type": "news",
            "institution": None,
            "reliability_score": 0.6,
        },
        {
            "name": "Prothom Alo (English) — national news",
            "url": "https://en.prothomalo.com",
            "source_type": "news",
            "institution": None,
            "reliability_score": 0.6,
        },
    ],
}

# alias lookup across all registered governments lives in seeds/__init__.py
