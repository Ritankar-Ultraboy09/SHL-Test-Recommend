from bs4 import BeautifulSoup
import requests
import json
import time 
from concurrent.futures import ThreadPoolExecutor, as_completed
import os 
import lxml



BASE_URL = "https://www.shl.com"
URL_CATALOGUE =  "https://www.shl.com/products/product-catalog/?start={start}&type=1&type=1"

PAGE_SIZE = 12
MAX_PAGES = 100
WORKERS = 8
DELAY = 0.3 
OUTPUT = "data/catalog.json"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


VALID_TYPES = set("ABCDEKPS")




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



def extract_listing(html:str)-> list[dict]:
    soup = BeautifulSoup(html, 'lxml')

    target_table = None

   

    for table in soup.find_all("table"):
        header = [th.get_text(strip=True) for th in table.find_all("th")]
        if any("Individual Test Solutions" in h for h in header):
            target_table = table
            break

    if not target_table:
        return []
    
    # rows = target_table.select("tr")[1:]
    # print(f"Total rows found: {len(rows)}")
    # if rows:
    #     first_row = rows[0]
    #     cells = first_row.find_all("td")
    #     print(f"Cells in first row: {len(cells)}")
    #     for j, cell in enumerate(cells):
    #         print(f"  cell[{j}]: '{cell.get_text(strip=True)}'") ##debug
    
    obj = []
    for row in target_table.select("tr"):
        cells = row.find_all("td")
        if len(cells)<4:
            continue


        link  = cells[0].find("a")
        if not link:
            continue
        name = link.get_text(strip=True)
        href = link.get("href", "")
        url = href if href.startswith("http") else BASE_URL + href

        remote = bool(cells[1].find("span", class_="catalogue__circle -yes"))
        adaptiveRt = bool(cells[2].find("span", class_="catalogue__circle -yes")) 

        types = cells[3].get_text(separator=" ", strip=True).upper()
        test_types = [t for t in cells[3].get_text(strip=True).upper() if t in VALID_TYPES]
        if not test_types:
            test_types = list(dict.fromkeys(
                t for t in types.split() if t in VALID_TYPES
            ))
            

        obj.append({
            "name": name,
            "url": url,
            "remote_testing": remote,
            "adaptive_rt": adaptiveRt,
            "test_types": test_types,
            "description": "",
            "job_levels": [], 
            "languages": [],
            "approx_duration in minutes": None,

        })

    return obj

def scrape_all_listings() -> list[dict]:
    listings = []
    for page_num in range(MAX_PAGES):
        start = page_num * PAGE_SIZE
        url = URL_CATALOGUE.format(start=start)
        print(f"page {page_num+1} start = {start}...", end ="")

        try:
            resp  = get(url)
            items = extract_listing(resp.text)
        except Exception as e:
            print(f"FAILED ({e}) — stopping")
            break

        print(f"{len(items)} items")

        if not items:
            break

        listings.extend(items)
        if len(items) < PAGE_SIZE:
            break

    return listings


def main():
    os.makedirs("data", exist_ok=True)

    print("=" * 55)
    print("Phase 1 — listing pages (requests + BS4)")
    print("=" * 55)
    raw = scrape_all_listings()

    if not raw:
        print("ERROR: nothing scraped — check URL or selectors")
        return


    with open("data/catalog_phase.json", "w") as f:
        json.dump(raw, f, indent=2)
    print(f"Phase 1 done — {len(raw)} items saved to data/catalog_phase.json")

if __name__ == "__main__":
    main()


        