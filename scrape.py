import os
import time
import cloudscraper
import requests
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
BASE_URL = "https://www.masstamilan.dev/movie-index"
DOWNLOAD_FOLDER = r"D:\music"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
scraper = cloudscraper.create_scraper()

def get_soup(url):
    try:
        response = scraper.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None
    except Exception as e:
        print(f"      [!] Error fetching: {url} -> {e}")
        return None

def start_recursive_download():
    print("--- STARTING MASSTAMILAN 320KBPS SCRAPER ---")
    main_soup = get_soup(BASE_URL)
    if not main_soup: return

    # 1. Get Years
    year_links = [a for a in main_soup.find_all('a', href=True) if a.text.strip().isdigit()]
    
    for y_tag in year_links:
        year_url = requests.compat.urljoin(BASE_URL, y_tag['href'])
        print(f"\n>>> [YEAR] {y_tag.text.strip()}")
        
        year_soup = get_soup(year_url)
        if not year_soup: continue
        
        # 2. Get Movies
        movie_links = year_soup.find_all('a', href=True)
        for m_tag in movie_links:
            href = m_tag['href']
            if "/movie/" in href or "/album/" in href or "-songs" in href:
                movie_page_url = requests.compat.urljoin(year_url, href)
                movie_name = m_tag.text.strip().replace(" ", "_")
                print(f"    > [MOVIE] {movie_name}")
                
                movie_soup = get_soup(movie_page_url)
                if not movie_soup: continue
                
                # 3. SPECIFIC SEARCH: Look for 'zip320' in the href
                target_link = None
                for a in movie_soup.find_all('a', href=True):
                    # Check if the URL contains 'zip320' as per your example
                    if "zip320" in a['href']:
                        target_link = requests.compat.urljoin(movie_page_url, a['href'])
                        break
                
                if target_link:
                    print(f"      [*] [FOUND] 320kbps Link: {target_link}")
                    # Since the URL doesn't end in .zip, we create a filename using the movie name
                    filename = f"{movie_name}_320kbps.zip"
                    save_path = os.path.join(DOWNLOAD_FOLDER, filename)
                    
                    if os.path.exists(save_path):
                        print("      [-] Already exists. Skipping.")
                        continue
                        
                    try:
                        print(f"      [Downloading] {filename}...")
                        with scraper.get(target_link, headers=HEADERS, stream=True) as r:
                            r.raise_for_status()
                            with open(save_path, 'wb') as f:
                                for chunk in r.iter_content(chunk_size=8192):
                                    f.write(chunk)
                        print(f"      [SUCCESS] Saved to {DOWNLOAD_FOLDER}")
                    except Exception as e:
                        print(f"      [!] Download Error: {e}")
                    
                    time.sleep(3) # Slightly longer delay to be safe
                else:
                    print("      [x] No 'zip320' link found on this page.")

if __name__ == "__main__":
    start_recursive_download()