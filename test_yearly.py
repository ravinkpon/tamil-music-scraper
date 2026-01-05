import os
import time
import cloudscraper
import requests
import re
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
# Base URL provided for the year 1998
YEAR_BASE_URL = "https://www.masstamilan.dev/browse-by-year/1998"
ROOT_DOWNLOAD_FOLDER = r"D:\music"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

# Automatically extract the year from the URL
year_match = re.search(r'/(\d{4})', YEAR_BASE_URL)
YEAR_FOLDER_NAME = year_match.group(1) if year_match else "Unknown_Year"
YEAR_PATH = os.path.join(ROOT_DOWNLOAD_FOLDER, YEAR_FOLDER_NAME)

os.makedirs(YEAR_PATH, exist_ok=True)
scraper = cloudscraper.create_scraper()

def log_status(message):
    log_file = os.path.join(YEAR_PATH, f"download_report_{YEAR_FOLDER_NAME}.txt")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")

def get_soup(url):
    try:
        time.sleep(1.5) 
        response = scraper.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        print(f"      [!] Error {response.status_code} for: {url}")
        return None
    except Exception as e:
        print(f"      [!] Connection Error: {e}")
        return None

def download_content(movie_url):
    soup = get_soup(movie_url)
    if not soup: return

    target_link = None
    file_type = ""
    
    # Sanitize movie name from URL
    base_name = movie_url.split('/')[-1].split('?')[0]
    movie_name = re.sub(r'[\\/*?:"<>|]', "", base_name).replace("-", "_")

    all_links = soup.find_all('a', href=True)
    
    for a in all_links:
        href = a['href']
        if "zip320" in href:
            target_link = requests.compat.urljoin(movie_url, href)
            file_type = "ALBUM_ZIP"
            break
            
    if not target_link:
        for a in all_links:
            href = a['href']
            if "d320" in href:
                target_link = requests.compat.urljoin(movie_url, href)
                file_type = "SINGLE_MP3"
                break

    if target_link:
        ext = ".zip" if file_type == "ALBUM_ZIP" else ".mp3"
        filename = f"{movie_name}_320kbps{ext}"
        save_path = os.path.join(YEAR_PATH, filename)
        
        if os.path.exists(save_path):
            print(f"      [-] Skipping: {filename} (Already exists)")
            return

        try:
            print(f"      [*] Downloading {filename}...")
            with scraper.get(target_link, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
            print(f"      [SUCCESS]")
            log_status(f"SUCCESS: {filename}")
        except Exception as e:
            print(f"      [!] Failed: {e}")
            log_status(f"FAILED: {filename} | {e}")
    else:
        print("      [x] No 320kbps link found on movie page.")

def scrape_entire_year():
    print(f"--- STARTING SESSION FOR YEAR: {YEAR_FOLDER_NAME} ---")
    current_page = 1
    
    while True:
        # Based on your URL, pagination is likely ?page=X or &page=X
        page_url = f"{YEAR_BASE_URL}?page={current_page}"
        print(f"\n[PAGE {current_page}] Fetching: {page_url}")
        
        soup = get_soup(page_url)
        if not soup: break

        # Scrape movie links
        movie_entries = []
        # On browse pages, movie links usually contain '-songs' or specific patterns
        for a in soup.find_all('a', href=True):
            href = a['href']
            # We target the actual song listing pages
            if "-songs" in href and "browse-by-year" not in href:
                full_url = requests.compat.urljoin(page_url, href)
                movie_entries.append((full_url, a.text.strip()))

        unique_movies = []
        seen = set()
        for url, title in movie_entries:
            if url not in seen and title:
                unique_movies.append((url, title))
                seen.add(url)

        if not unique_movies:
            print(f"--- No more movies found. Finishing Year {YEAR_FOLDER_NAME}. ---")
            break

        print(f"Found {len(unique_movies)} items on this page. Processing...")
        for movie_url, title in unique_movies:
            print(f"  > Processing Movie: {title}")
            download_content(movie_url)
        
        current_page += 1

if __name__ == "__main__":
    scrape_entire_year()