"""
Menu loader for ICB Q Assistant.
Parses the raw menu JSON + analytics CSV into a structured format
suitable for injection into the Q system prompt.
"""

import json
import csv
import os
from collections import defaultdict
from typing import Optional


FOOD_CATEGORIES = {
    "Bar Nibbles", "Small Plates", "Sharing Plates", "From The Clay Oven",
    "Salads & Burger", "Momos, Dimsum & Bao", "Pizza", "Pasta & Grills",
    "Sides & Add Ons", "Large Plates - North Indian", "Large Plates - South Indian",
    "Pan Asian", "Lentils, Staples & Breads", "Dessert", "Sushi",
}

DRINK_CATEGORIES = {
    "Craft Beer", "Signature Cocktails", "Classic Cocktail", "Ipl Cocktails",
    "Mocktail", "Iced Tea", "Soft Beverages", "Whisky", "International Whiskey",
    "Single Malts", "Vodka", "Gin", "Rum", "Tequila/Mezcal", "Liqueurs",
    "Cognac/Brandy", "Red Wine", "White Wines", "Rose Wine",
    "Sparkling Wine/Champagne", "Wine C Ocktails", "Shooter",
    "(High Abv) Contains 100 Ml Alcohol", "Liquor Offer Price",
}

# Tier thresholds (based on actual ICB data: max ~1684 orders)
TIER_HOT     = 800   # ★★★ very frequently ordered
TIER_POPULAR = 300   # ★★  often ordered
TIER_ORDERED = 50    # ★   ordered at least occasionally


def load_analytics(csv_path: str) -> tuple[dict, dict]:
    """
    Parse the analytics CSV.

    Returns:
        popularity_scores : dict[item_id_str -> int]   (No. of Times Ordered)
        co_order_map      : dict[item_name_str -> str] (Most Co-Ordered With)
    """
    popularity_scores = {}
    co_order_map = {}

    if not os.path.exists(csv_path):
        return popularity_scores, co_order_map

    with open(csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            item_id = str(row.get("Item ID", "")).strip()
            times   = row.get("No. of Times Ordered", "0").strip()
            co      = row.get("Most Co-Ordered With", "").strip()
            name    = row.get("Item Name", "").strip()
            try:
                popularity_scores[item_id] = int(times)
            except ValueError:
                pass
            if co and name:
                co_order_map[name] = co

    return popularity_scores, co_order_map


def load_menu(
    json_path: str,
    analytics_csv_path: Optional[str] = None,
    popularity_scores: Optional[dict] = None,
) -> dict:
    """
    Load and parse the menu JSON, enriched with analytics data.

    Args:
        json_path:          Path to the menu JSON file.
        analytics_csv_path: Path to the analytics CSV (preferred source).
        popularity_scores:  Fallback dict mapping item_id (str) -> score,
                            used only if analytics_csv_path is not provided.

    Returns a dict with:
        items          : list of enriched item dicts
        categories     : dict id -> name
        by_category    : dict category_name -> list of items
        menu_text      : formatted string for system prompt
        popular_text   : natural-language popular dishes description
        co_order_map   : dict item_name -> most co-ordered item name
    """
    # Load analytics
    co_order_map = {}
    if analytics_csv_path:
        scores_from_csv, co_order_map = load_analytics(analytics_csv_path)
        if not popularity_scores:
            popularity_scores = scores_from_csv

    with open(json_path, "r") as f:
        data = json.load(f)

    raw_cats  = {c["id"]: c["name"] for c in data["entity"]["main_categories"]}
    raw_items = data["entity"]["items"]

    items = []
    for it in raw_items:
        if not it.get("enable") or not it.get("in_stock"):
            continue
        cat_name  = raw_cats.get(it["category_id"], it["category_id"])
        pop_score = (popularity_scores or {}).get(str(it["id"]), 0)
        items.append(
            {
                "id":               it["id"],
                "name":             it["name"],
                "category":         cat_name,
                "category_id":      it["category_id"],
                "is_veg":           it.get("is_veg", False),
                "price":            it.get("price", 0),
                "description":      (it.get("description") or "").strip(),
                "recommended":      it.get("recommended", False),
                "spice_level":      (it.get("catalog_attributes") or {}).get("spice_level", ""),
                "popularity_score": pop_score,
                "co_ordered_with":  co_order_map.get(it["name"], ""),
            }
        )

    # Sort: hottest first within each category
    items.sort(key=lambda x: (-x["popularity_score"], x["name"]))

    by_category = defaultdict(list)
    for it in items:
        by_category[it["category"]].append(it)

    # Top popular items overall (real order data)
    popular_items = sorted(
        [i for i in items if i["popularity_score"] >= TIER_POPULAR],
        key=lambda x: -x["popularity_score"],
    )[:20]
    if not popular_items:
        popular_items = [i for i in items if i["recommended"]]

    menu_text    = _build_menu_text(by_category)
    popular_text = _build_popular_text(popular_items)

    return {
        "items":        items,
        "categories":   raw_cats,
        "by_category":  dict(by_category),
        "menu_text":    menu_text,
        "popular_text": popular_text,
        "co_order_map": co_order_map,
        "popular_items": popular_items,
    }


def _popularity_tag(score: int) -> str:
    if score >= TIER_HOT:
        return " 🔥"        # very hot
    if score >= TIER_POPULAR:
        return " ★"         # popular
    if score >= TIER_ORDERED:
        return ""
    return ""


def _build_menu_text(by_category: dict) -> str:
    """Build a compact, LLM-friendly menu string sorted by popularity within each category."""
    lines = []

    food_cats  = sorted([k for k in by_category if k in FOOD_CATEGORIES])
    drink_cats = sorted([k for k in by_category if k in DRINK_CATEGORIES])
    other_cats = sorted([k for k in by_category if k not in FOOD_CATEGORIES and k not in DRINK_CATEGORIES])

    for section_label, cat_list in [
        ("── FOOD ──", food_cats),
        ("── DRINKS ──", drink_cats),
        ("── OTHER ──", other_cats),
    ]:
        if not cat_list:
            continue
        lines.append(f"\n{section_label}")
        for cat_name in cat_list:
            cat_items = by_category[cat_name]
            lines.append(f"\n[{cat_name}]")
            for it in cat_items:
                veg_tag = "Veg" if it["is_veg"] else "Non-Veg"
                pop_tag = _popularity_tag(it["popularity_score"])
                co_tag  = f" | pairs well with: {it['co_ordered_with']}" if it["co_ordered_with"] else ""
                desc    = it["description"]
                if desc and len(desc) > 80:
                    desc = desc[:77] + "..."
                desc_str = f" | {desc}" if desc else ""
                lines.append(
                    f"  • [{it['id']}] {it['name']} ({veg_tag}, ₹{it['price']}){pop_tag}{desc_str}{co_tag}"
                )
    return "\n".join(lines)


def _build_popular_text(popular_items: list) -> str:
    if not popular_items:
        return ""

    # Split into food vs drinks
    food  = [i for i in popular_items if i["category"] in FOOD_CATEGORIES][:8]
    drinks= [i for i in popular_items if i["category"] in DRINK_CATEGORIES][:5]

    lines = []
    if food:
        lines.append("Most ordered food: " + ", ".join(i["name"] for i in food))
    if drinks:
        lines.append("Most ordered drinks: " + ", ".join(i["name"] for i in drinks))

    return " | ".join(lines)
