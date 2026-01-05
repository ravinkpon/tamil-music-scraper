import os
import time
import cloudscraper
import requests
import re  # Added for filename cleaning
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
MOVIE_URL = "https://www.masstamilan.dev/arasan-2025-songs" 
DOWNLOAD_FOLDER = r"D:\music"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
scraper = cloudscraper.create_scraper()

def sanitize_filename(name):
    """Removes characters that are illegal in Windows filenames."""
    # Removes \ / : * ? " < > |
    return re.sub(r'[\\/*?:"<>|]', "", name)

def download_movie_content(url):
    print(f"--- Analyzing Page: {url} ---")
    
    try:
        response = scraper.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
    except Exception as e:
        print(f"[!] Error: {e}")
        return

    target_link = None
    file_type = ""
    
    # FIX: Get name before the '?' and clean it
    # Example: 'star-2024-songs?ref=search' becomes 'star_2024_songs'
    base_name = url.split('/')[-1].split('?')[0]
    movie_name = sanitize_filename(base_name).replace("-", "_")

    # SEARCH LOGIC
    all_links = soup.find_all('a', href=True)
    
    # 1. Check for Album ZIP
    for a in all_links:
        if "zip320" in a['href']:
            target_link = requests.compat.urljoin(url, a['href'])
            file_type = "ALBUM_ZIP"
            break
            
    # 2. Fallback to Single Song (d320)
    if not target_link:
        for a in all_links:
            if "d320" in a['href']:
                target_link = requests.compat.urljoin(url, a['href'])
                file_type = "SINGLE_MP3"
                break

    if target_link:
        print(f"[FOUND] Type: {file_type} | Link: {target_link}")
        
        ext = ".zip" if file_type == "ALBUM_ZIP" else ".mp3"
        filename = f"{movie_name}_320kbps{ext}"
        save_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        try:
            print(f"[START] Downloading {filename}...")
            # Use scraper here to maintain the bypass session
            with scraper.get(target_link, headers=HEADERS, stream=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
            
            print(f"[SUCCESS] Saved to: {save_path}")
        except Exception as e:
            print(f"[!] Download Failed: {e}")
    else:
        print("[FAIL] Neither 'zip320' nor 'd320' links were found.")

if __name__ == "__main__":
    download_movie_content(MOVIE_URL)