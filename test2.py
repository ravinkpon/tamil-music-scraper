import os
import time
import cloudscraper
import requests
import re
import zipfile  # New library to handle the zip repair
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
MOVIE_URL = "https://www.masstamilan.dev/star-2024-songs?ref=search" 
DOWNLOAD_FOLDER = r"D:\music"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.google.com/",
}

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
scraper = cloudscraper.create_scraper()

def sanitize_filename(name):
    return re.sub(r'[\\/*?:"<>|]', "", name)

def repair_zip(file_path):
    """Attempt to fix common zip header issues so Windows can open it."""
    temp_path = file_path + ".tmp"
    try:
        with zipfile.ZipFile(file_path, 'r') as z_in:
            with zipfile.ZipFile(temp_path, 'w') as z_out:
                for item in z_in.infolist():
                    z_out.writestr(item, z_in.read(item.filename))
        os.remove(file_path)
        os.rename(temp_path, file_path)
        print(f"      [FIXED] Zip header repaired for Windows compatibility.")
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        print(f"      [WARNING] Could not repair zip: {e}")

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
    base_name = url.split('/')[-1].split('?')[0]
    movie_name = sanitize_filename(base_name).replace("-", "_")

    all_links = soup.find_all('a', href=True)
    for a in all_links:
        if "zip320" in a['href']:
            target_link = requests.compat.urljoin(url, a['href'])
            file_type = "ALBUM_ZIP"
            break
            
    if not target_link:
        for a in all_links:
            if "d320" in a['href']:
                target_link = requests.compat.urljoin(url, a['href'])
                file_type = "SINGLE_MP3"
                break

    if target_link:
        ext = ".zip" if file_type == "ALBUM_ZIP" else ".mp3"
        filename = f"{movie_name}_320kbps{ext}"
        save_path = os.path.join(DOWNLOAD_FOLDER, filename)
        
        try:
            print(f"[START] Downloading {filename}...")
            # Using allow_redirects=True is important for these downloader links
            with scraper.get(target_link, headers=HEADERS, stream=True, allow_redirects=True) as r:
                r.raise_for_status()
                with open(save_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=1024*1024):
                        if chunk:
                            f.write(chunk)
            
            # If it's a zip, try to repair it immediately
            if file_type == "ALBUM_ZIP":
                repair_zip(save_path)
                
            print(f"[SUCCESS] Saved: {save_path}")
        except Exception as e:
            print(f"[!] Download Failed: {e}")
    else:
        print("[FAIL] No link found.")

if __name__ == "__main__":
    download_movie_content(MOVIE_URL)