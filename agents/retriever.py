import json
from config import CAT_PATH, TOP_K

with open(CAT_PATH, "r", encoding="utf-8") as f:
    TOTAL_CAT = json.load(f)

VALID_URLS = {item["url"] for item in TOTAL_CAT}

def normalize(text:str) -> str:
    return text.replace(".net", "dotnet").replace(".", "").replace(" ", "").lower()


def filter_retrieve(intent: dict) -> list[dict]:
    test_types = intent.get("test_types", [])
    keywords   = [kw.lower() for kw in intent.get("keywords", [])]
    level      = intent.get("level", "").lower()

    results = []

    for item in TOTAL_CAT:
        if test_types:
            if not any(t in item.get("test_types", []) for t in test_types):
                continue

        score = 0
        name = item.get("name", "").lower()
        description = item.get("description", "").lower()

        for kw in keywords:
            kw_norm   = normalize(kw)
            name_norm = normalize(name)
            desc_norm = normalize(description)

            if kw_norm in name_norm:
                score += 2   
            if kw_norm in desc_norm:
                score += 1  

        if level and level != "any":
            job_levels = [l.lower() for l in item.get("job_levels", [])]
            if any(level in l for l in job_levels):
                score += 1

        
        results.append((score, item))

    results.sort(key=lambda x: x[0], reverse=True)
    return [item for score, item in results[:TOP_K]]

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