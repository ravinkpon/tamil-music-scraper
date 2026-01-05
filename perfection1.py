import os
import time
import cloudscraper
import re
from bs4 import BeautifulSoup
import requests

# --- CONFIGURATION ---
START_YEAR = 2005
END_YEAR = 2026
ROOT_DOWNLOAD_FOLDER = r"Z:\music"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

YEARS_TO_DOWNLOAD = [str(y) for y in range(START_YEAR, END_YEAR + 1)]
scraper = cloudscraper.create_scraper()

# --- HELPER FUNCTIONS ---

def get_soup(url):
    try:
        time.sleep(1.2) 
        response = scraper.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            return BeautifulSoup(response.text, 'html.parser')
        return None
    except Exception:
        return None

def download_movie_content(movie_url, year_path):
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
            print(f"      [-] Skipping: {filename}")
            return True

        try:
            print(f"      [*] Downloading {filename}...")
            with scraper.get(target_link, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk: f.write(chunk)
            print(f"      [SUCCESS]")
            return True
        except Exception as e:
            print(f"      [!] Failed: {e}")
            return False
    return False

# --- MAIN EXECUTION ---

def run_yearly_automated_scrape(mode="test"):
    
    test_dir = os.path.join(ROOT_DOWNLOAD_FOLDER, "test_reports")
    
    if mode == "test":
        os.makedirs(test_dir, exist_ok=True)
        print(f"TEST MODE: Reports saved to {test_dir}")
        print("\nprogressing......")

    for year in YEARS_TO_DOWNLOAD:
        year_base_url = f"https://www.masstamilan.dev/browse-by-year/{year}"
        
        if mode == "test":
            current_save_path = test_dir
        else:
            current_save_path = os.path.join(ROOT_DOWNLOAD_FOLDER, year)
            os.makedirs(current_save_path, exist_ok=True)

        print(f"\n" + "="*60)
        print(f"--- STARTING {mode.upper()} FOR YEAR: {year} ---")
        
        current_page = 1
        global_seen_urls = set()
        report_entries = []

        while True:
            page_url = f"{year_base_url}?page={current_page}"
            soup = get_soup(page_url)
            if not soup: break

            # Specifically target the grid structure observed in your screenshots
            main_grid = soup.find('div', class_='gw') or soup.find('section', class_='bots')
            if not main_grid: break

            # Find each movie block (usually div with class a-i or similar)
            movie_blocks = main_grid.find_all('div', class_='a-i')
            
            # Fallback if specific div blocks aren't found
            if not movie_blocks:
                links = main_grid.find_all('a', href=True)
            else:
                links = [block.find('a', href=True) for block in movie_blocks if block.find('a', href=True)]

            found_new_on_page = False
            for a in links:
                href = a['href']
                # Get the full text for the metadata spacing
                raw_text = a.get_text(separator="\n").strip() 
                
                if "-songs" in href and raw_text and "browse-by-year" not in href:
                    full_url = requests.compat.urljoin(page_url, href)
                    if full_url not in global_seen_urls:
                        global_seen_urls.add(full_url)
                        found_new_on_page = True
                        
                        # Formatting the entry with specific spacing
                        # We split by newlines to separate Movie Name from Starring/Director info
                        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                        movie_title = lines[0] if lines else "Unknown Movie"
                        metadata = " | ".join(lines[1:]) if len(lines) > 1 else ""

                        if mode == "test":
                            entry = f"MOVIE: {movie_title}\nDETAILS: {metadata}\nURL: {full_url}\n{'-'*40}"
                            report_entries.append(entry)
                        else:
                            success = download_movie_content(full_url, current_save_path)
                            status = "SUCCESS" if success else "FAILED"
                            entry = f"[{status}] MOVIE: {movie_title}\nURL: {full_url}\n{'-'*40}"
                            report_entries.append(entry)

            if not found_new_on_page: break
            current_page += 1

        # Save report with refined spacing
        report_name = f"verified_list_{year}.txt" if mode == "test" else f"download_report_{year}.txt"
        final_report_path = os.path.join(current_save_path, report_name)
        
        with open(final_report_path, "w", encoding="utf-8") as f:
            f.write(f"--- {mode.upper()} REPORT FOR {year} ---\n")
            f.write(f"Total Unique Movies Found: {len(report_entries)}\n")
            f.write("="*60 + "\n\n")
            f.write("\n\n".join(report_entries)) # Double spacing between movies
        
        print(f"Done with {year}. Unique Movies: {len(report_entries)}")

if __name__ == "__main__":
    run_yearly_automated_scrape(mode="download")

    # change "test" to "download" for actually download