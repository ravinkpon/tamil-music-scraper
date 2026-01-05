import os
import time
import cloudscraper
import requests
import re
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
YEAR_BASE_URL = "https://www.masstamilan.dev/browse-by-year/1999"
ROOT_DOWNLOAD_FOLDER = r"D:\music"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

# Extract Year and create folder
year_match = re.search(r'/(\d{4})', YEAR_BASE_URL)
YEAR_FOLDER_NAME = year_match.group(1) if year_match else "Unknown_Year"
YEAR_PATH = os.path.join(ROOT_DOWNLOAD_FOLDER, YEAR_FOLDER_NAME)

os.makedirs(YEAR_PATH, exist_ok=True)
scraper = cloudscraper.create_scraper()

def sanitize_filename(name):
    """Removes characters that are illegal in Windows filenames."""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def get_soup(url):
    try:
        time.sleep(1.5) 
        response = scraper.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None
    except Exception:
        return None

def download_movie_content(movie_url):
    """Finds and downloads 320kbps ZIP or MP3."""
    soup = get_soup(movie_url)
    if not soup: return

    target_link = None
    file_type = ""
    
    # Extract and clean movie name
    base_name = movie_url.split('/')[-1].split('?')[0]
    movie_name = sanitize_filename(base_name).replace("-", "_")

    all_links = soup.find_all('a', href=True)
    for a in all_links:
        if "zip320" in a['href']:
            target_link = requests.compat.urljoin(movie_url, a['href'])
            file_type = "zip"
            break
            
    if not target_link:
        for a in all_links:
            if "d320" in a['href']:
                target_link = requests.compat.urljoin(movie_url, a['href'])
                file_type = "mp3"
                break

    if target_link:
        ext = ".zip" if file_type == "zip" else ".mp3"
        filename = f"{movie_name}_320kbps{ext}"
        save_path = os.path.join(YEAR_PATH, filename)
        
        if os.path.exists(save_path):
            print(f"      [-] Already exists: {filename}")
            return

        try:
            print(f"      [*] Downloading {filename}...")
            with scraper.get(target_link, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
            print(f"      [SUCCESS]")
        except Exception as e:
            print(f"      [!] Download failed: {e}")
    else:
        print("      [x] No 320kbps links found.")

def scrape_entire_year():
    print(f"--- STARTING SESSION FOR YEAR: {YEAR_FOLDER_NAME} ---")
    current_page = 1
    
    while True:
        page_url = f"{YEAR_BASE_URL}?page={current_page}"
        print(f"\n[PAGE {current_page}] Reading index...")
        
        soup = get_soup(page_url)
        if not soup: break

        # TARGET THE MAIN CONTENT ONLY: Ignore sidebars
        # We look for the <table> tag which contains the year's movie list
        main_table = soup.find('table')
        search_area = main_table if main_table else soup

        movie_links = []
        for a in search_area.find_all('a', href=True):
            href = a['href']
            # Only pick links that look like movie pages and aren't navigation links
            if "-songs" in href and "browse-by-year" not in href:
                # Extra check to ensure we aren't clicking sidebar trending items
                full_url = requests.compat.urljoin(page_url, href)
                movie_links.append((full_url, a.text.strip()))

        unique_movies = []
        seen = set()
        for url, title in movie_links:
            if url not in seen and title:
                unique_movies.append((url, title))
                seen.add(url)

        if not unique_movies:
            print(f"--- Finished all movies for {YEAR_FOLDER_NAME}. ---")
            break

        print(f"Found {len(unique_movies)} actual movies on this page.")
        for movie_url, title in unique_movies:
            print(f"  > Processing: {title}")
            # MATCHED FUNCTION NAME HERE
            download_movie_content(movie_url)
        
        current_page += 1

if __name__ == "__main__":
    scrape_entire_year()