"""
Remembench — Industry Registry API

Serves the industry configuration to the frontend so dropdowns,
market lists, and category filters can be populated dynamically.
Adding a new industry to the backend registry automatically
makes it available in the UI.
"""

from fastapi import APIRouter

from app.industries import INDUSTRIES, get_industry_groups

router = APIRouter()


@router.get("/")
async def list_industries() -> dict:
    """
    Return all configured industries grouped by vertical.

    Used by the frontend to populate the industry switcher,
    market dropdown, and category filters dynamically.
    """
    groups = get_industry_groups()

    result = {}
    for group_key, configs in groups.items():
        result[group_key] = [
            {
                "key": c.key,
                "label": c.label,
                "icon": c.icon,
                "description": c.description,
                "markets": [
                    {"geo_label": m.geo_label, "latitude": m.latitude, "longitude": m.longitude}
                    for m in c.markets
                ],
                "categories": c.categories,
                "category_labels": c.category_labels,
            }
            for c in configs
        ]

    return {"groups": result}
