import os
import time
import cloudscraper
import re
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
START_YEAR = 2001
END_YEAR = 2004
ROOT_DOWNLOAD_FOLDER = r"Z:\music" # change
MAX_YEARS_AT_ONCE = 1  # How many years to download simultaneously
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

YEARS_TO_DOWNLOAD = [str(y) for y in range(START_YEAR, END_YEAR + 1)]
scraper = cloudscraper.create_scraper()

# --- HELPER FUNCTIONS ---

def get_soup(url):
    try:
        time.sleep(0.5) 
        response = scraper.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None
    except Exception:
        return None

def download_movie_content(movie_url, year_path, year_label):
    """Downloads a single movie album"""
    soup = get_soup(movie_url)
    if not soup: return False

    target_link = None
    file_type = ""
    
    base_name = movie_url.split('/')[-1].split('?')[0]
    movie_name = re.sub(r'[\\/*?:"<>|]', "", base_name).replace("-", "_")

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
        save_path = os.path.join(year_path, filename)
        
        if os.path.exists(save_path):
            print(f"[{year_label}] Skipping: {filename}")
            return True

        try:
            print(f"[{year_label}] Downloading {filename}...")
            with scraper.get(target_link, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
            print(f"[{year_label}] SUCCESS: {filename}")
            return True
        except Exception as e:
            print(f"[{year_label}] FAILED {filename}: {e}")
            return False
    return False

# --- CORE LOGIC ---

def process_single_year(year, mode):
    """This function handles one whole year from start to finish"""
    year_base_url = f"https://www.masstamilan.dev/browse-by-year/{year}"
    
    # Setup paths
    if mode == "test":
        current_save_path = os.path.join(ROOT_DOWNLOAD_FOLDER, "test_reports")
    else:
        current_save_path = os.path.join(ROOT_DOWNLOAD_FOLDER, year)
    
    os.makedirs(current_save_path, exist_ok=True)
    
    print(f"\n>>> STARTED PROCESSING YEAR: {year} <<<")
    
    current_page = 1
    global_seen_urls = set()
    report_data = []

    while True:
        page_url = f"{year_base_url}?page={current_page}"
        soup = get_soup(page_url)
        if not soup: break

        main_grid = soup.find('div', class_='gw') or soup.find('section', class_='bots')
        if not main_grid: break

        page_movies = []
        for a in main_grid.find_all('a', href=True):
            href = a['href']
            text = a.text.strip()
            if "-songs" in href and text and "browse-by-year" not in href:
                full_url = requests.compat.urljoin(page_url, href)
                if full_url not in global_seen_urls:
                    page_movies.append((full_url, text))
                    global_seen_urls.add(full_url)

        if not page_movies: break

        # Process movies within this year sequentially
        for movie_url, title in page_movies:
            if mode == "test":
                report_data.append(f"Movie: {title} | URL: {movie_url}")
            else:
                success = download_movie_content(movie_url, current_save_path, year)
                status = "SUCCESS" if success else "FAILED"
                report_data.append(f"[{status}] Movie: {title} | URL: {movie_url}")
        
        current_page += 1

    # Save Year Report
    report_name = f"verified_list_{year}.txt" if mode == "test" else f"download_report_{year}.txt"
    final_report_path = os.path.join(current_save_path, report_name)
    
    with open(final_report_path, "w", encoding="utf-8") as f:
        f.write(f"--- {mode.upper()} REPORT FOR {year} ---\n")
        f.write(f"Total Movies Found: {len(report_data)}\n\n")
        f.write("\n".join(report_data))
    
    return f"Year {year} complete. Movies: {len(report_data)}"

def run_multithreaded_years(mode="test"):
    print(f"Starting Multi-Year Scrape (Mode: {mode})")
    print(f"Parallel Years: {MAX_YEARS_AT_ONCE}")
    
    # ThreadPoolExecutor is now at the YEAR level
    with ThreadPoolExecutor(max_workers=MAX_YEARS_AT_ONCE) as executor:
        future_to_year = {executor.submit(process_single_year, year, mode): year for year in YEARS_TO_DOWNLOAD}
        
        for future in as_completed(future_to_year):
            year_completed = future_to_year[future]
            try:
                result = future.result()
                print(f"FINISH: {result}")
            except Exception as e:
                print(f"ERROR processing year {year_completed}: {e}")

if __name__ == "__main__":
    # Use "prod" to download, "test" to just list
    run_multithreaded_years(mode="prod")