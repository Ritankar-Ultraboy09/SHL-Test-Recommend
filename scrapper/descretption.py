from bs4 import BeautifulSoup
import requests
import json
import time 
import lxml
import re

PATH =  "data/catalog_phase.json"
DELAY = 0.3
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

def get(url: str, retry : int = 3)-> requests.Response:
    for attempt in range(retry):
        try:
            response = requests.get(url, headers=HEADERS, timeout= 15)
            response.raise_for_status()
            time.sleep(DELAY)
            return response 
        except requests.RequestException as e:
            if attempt == retry -1:
                raise 
            time.sleep(2 ** attempt)

def descrption(item: dict)->dict:
    try:
        response = get(item["url"])
        soup = BeautifulSoup(response.text, 'lxml')

        for h4 in soup.find_all("h4"):
            heading = h4.get_text(strip=True).lower()
            nxt = h4.find_next_sibling()   
            if not nxt:
                continue
            if heading == "description":
                item["description"] = nxt.get_text(strip=True)

            elif heading == "job levels":
                item["job_levels"] = [
                    l.strip() for l in nxt.get_text(strip=True).split(",")
                    if l.strip()
                ]

            elif heading == "languages":
                item["languages"] = [
                    l.strip() for l in nxt.get_text(strip=True).split(",")
                    if l.strip()
                ]

            elif heading == "assessment length":
                text = nxt.get_text(strip=True)
                dur = re.search(r"(\d+)", text)
                if dur:
                    item["approx_duration in minutes"] = int(dur.group(1))

    except Exception as e:
        print(f"\n  WARN  {item['name'][:50]}: {e}")

    return item

def main():
    with open(PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    print(f"Loaded {len(data)} items from {PATH}")
    for i, item in enumerate(data):
        print(f"  {i+1}/{len(data)}  {item['name'][:60]}")
        descrption(item)

        if (i + 1) % 10 == 0:
            with open(PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"\nDone. {PATH} updated.")
    _summary(data)


def _summary(items):
    no_desc     = sum(1 for i in items if not i.get("description"))
    no_levels   = sum(1 for i in items if not i.get("job_levels"))
    no_langs    = sum(1 for i in items if not i.get("languages"))
    no_duration = sum(1 for i in items if not i.get("approx_duration in minutes"))
    print(f"\n── Summary ──────────────────────────────")
    print(f"  Missing description  : {no_desc}")
    print(f"  Missing job_levels   : {no_levels}")
    print(f"  Missing languages    : {no_langs}")
    print(f"  Missing duration     : {no_duration}")


if __name__ == "__main__":
    main()
    



