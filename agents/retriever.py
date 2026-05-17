import json
from config import CAT_PATH, TOP_K

with open(CAT_PATH, "r", encoding="utf-8") as f:
    TOTAL_CAT = json.load(f)

VALID_URLS = {item["url"] for item in TOTAL_CAT}

def normalize(text:str) -> str:
    return text.replace(".net", "dotnet").replace(".", "").replace(" ", "").lower()

def _score_items(catalog, keywords, level, test_types=None, original_keywords=None):
    original_keywords = [k.lower() for k in (original_keywords or [])]
    results = []
    for item in catalog:
        if test_types and not any(t in item.get("test_types", []) for t in test_types):
            continue
        score = 0
        name  = item.get("name", "").lower()
        desc  = item.get("description", "").lower()
        for kw in keywords:
            kw_norm   = kw.replace(".net", "dotnet").replace(".", "").replace(" ", "").lower()
            name_norm = name.replace(".net", "dotnet").replace(".", "").replace(" ", "").lower()
            desc_norm = desc.replace(".net", "dotnet").replace(".", "").replace(" ", "").lower()
            weight = 3 if kw in original_keywords else 1
            if kw_norm in name_norm:
                score += 2 * weight
            if kw_norm in desc_norm:
                score += 1 * weight
        if level and level != "any":
            job_levels = [l.lower() for l in item.get("job_levels", [])]
            if any(level in l for l in job_levels):
                score += 1
        results.append((score, item))
    results.sort(key=lambda x: x[0], reverse=True)
    return results

    
def filter_retrieve(intent: dict) -> list[dict]:
    test_types = intent.get("test_types", [])
    keywords   = [kw.lower() for kw in intent.get("keywords", [])]
    original_keywords = [kw.lower() for kw in intent.get("original_keywords", [])]
    level      = intent.get("level", "").lower()

    print(f"ORIGINAL KEYWORDS: {original_keywords}")  # ← add this
    print(f"ALL KEYWORDS: {keywords}")

    if len(test_types) > 1:
        per_type = []
        for t in test_types:
            type_catalog = [i for i in TOTAL_CAT if t in i.get("test_types", [])]
            type_results = _score_items(type_catalog, keywords, level, original_keywords=original_keywords)
            relevant = [(s, i) for s, i in type_results if s > 0]
            if not relevant:
                relevant = type_results[:1]
            per_type.extend(relevant[:3])

        seen   = set()
        merged = []
        for score, item in sorted(per_type, key=lambda x: x[0], reverse=True):
            if item["url"] not in seen:
                seen.add(item["url"])
                merged.append((score, item))
        return [item for score, item in merged[:TOP_K]]

    return [item for score, item in _score_items(TOTAL_CAT, keywords, level, test_types, original_keywords)[:TOP_K]]

def is_valid_url(url: str) -> bool:
    return url in VALID_URLS

def by_name(name: str) -> dict | None:
    name_lower = name.lower().strip()
    for item in TOTAL_CAT:
        if item.get("name", "").lower().strip() == name_lower:
            return item
    for item in TOTAL_CAT:
        if name_lower in item.get("name", "").lower():
            return item
    
    return None

def get_all() -> list[dict]:
    return TOTAL_CAT