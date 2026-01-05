import os
import time
import cloudscraper
import re
from bs4 import BeautifulSoup
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- CONFIGURATION ---
START_YEAR = 2000
END_YEAR =  2026
ROOT_DOWNLOAD_FOLDER = r"/mnt/storage/music"
MAX_WORKERS = 5  # Number of simultaneous downloads/requests
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

YEARS_TO_DOWNLOAD = [str(y) for y in range(START_YEAR, END_YEAR + 1)]
scraper = cloudscraper.create_scraper()

# --- HELPER FUNCTIONS ---

def get_soup(url):
    try:
        # Reduced sleep slightly as threads will distribute the load
        time.sleep(0.5) 
        response = scraper.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None
    except Exception:
        return None

def download_movie_content(movie_url, year_path):
    """Function to be executed by threads for actual downloading"""
    soup = get_soup(movie_url)
    if not soup: return False

    target_link = None
    file_type = ""
    
    base_name = movie_url.split('/')[-1].split('?')[0]
    movie_name = re.sub(r'[\\/*?:"<>|]', "", base_name).replace("-", "_")

    all_links = soup.find_all('a', href=True)
    # Search for ZIP first, then MP3
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
            print(f"      [-] Skipping: {filename}")
            return True

        try:
            print(f"      [*] Downloading {filename}...")
            with scraper.get(target_link, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
            print(f"      [SUCCESS] Finished {filename}")
            return True
        except Exception as e:
            print(f"      [!] Failed {filename}: {e}")
            return False
    return False

# --- MAIN EXECUTION ---

def process_movie(movie_info, mode, current_save_path):
    """Wrapper for the worker threads to return status and data"""
    movie_url, title = movie_info
    if mode == "test":
        return f"Movie: {title} | URL: {movie_url}"
    else:
        success = download_movie_content(movie_url, current_save_path)
        status = "SUCCESS" if success else "FAILED"
        return f"[{status}] Movie: {title} | URL: {movie_url}"

def run_yearly_automated_scrape(mode="test"):
    test_dir = os.path.join(ROOT_DOWNLOAD_FOLDER, "test_reports")
    
    if mode == "test":
        os.makedirs(test_dir, exist_ok=True)
        print(f"TEST MODE: All reports will be saved to {test_dir}")

    for year in YEARS_TO_DOWNLOAD:
        year_base_url = f"https://www.masstamilan.dev/browse-by-year/{year}"
        
        if mode == "test":
            current_save_path = test_dir
        else:
            current_save_path = os.path.join(ROOT_DOWNLOAD_FOLDER, year)
            os.makedirs(current_save_path, exist_ok=True)

        print(f"\n" + "="*60)
        print(f"--- PROCESSING {mode.upper()} FOR YEAR: {year} ---")
        
        current_page = 1
        global_seen_urls = set()
        report_data = []

        # ThreadPoolExecutor handles the parallel execution
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
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

                # Map the movies on this page to worker threads
                future_to_movie = {executor.submit(process_movie, movie, mode, current_save_path): movie for movie in page_movies}
                
                for future in as_completed(future_to_movie):
                    result = future.result()
                    report_data.append(result)
                
                current_page += 1

        # Save Report
        report_name = f"verified_list_{year}.txt" if mode == "test" else f"download_report_{year}.txt"
        final_report_path = os.path.join(current_save_path, report_name)
        
        with open(final_report_path, "w", encoding="utf-8") as f:
            f.write(f"--- {mode.upper()} REPORT FOR {year} ---\n")
            f.write(f"Total Movies Found: {len(report_data)}\n\n")
            f.write("\n".join(report_data))
        
        print(f"Done with {year}. Unique Movies Processed: {len(report_data)}")

if __name__ == "__main__":
    # Change to "prod" or similar to actually download
    run_yearly_automated_scrape(mode="prod")