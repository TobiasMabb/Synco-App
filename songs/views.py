import os
import re
import requests
import json # Dinagdag ko ito para hindi mag-error yung json.loads mo sa ilalim
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Song  # Siguraduhing tugma sa pangalan ng iyong Model (singular)
from bs4 import BeautifulSoup
import cloudscraper


# Common Headers para sa mga out-bound API requests
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# =========================================================================
# 0. TEXT FORMATTING & TRANSPOSE ENGINE UTILITIES
# =========================================================================

def clean_chords_formatting(text):
    """
    Linilinis ang magulong spaces, tabs, at mga paulit-ulit na bakanteng linya
    mula sa mga nakalap na chord scrapers para maging presentable.
    """
    if not text:
        return ""
    # Palitan ang tabs ng 4 spaces para sa monospace alignment
    text = text.replace('\t', '    ')
    # Tanggalin ang mga redundant na white spaces sa dulo ng bawat linya
    text = '\n'.join([line.rstrip() for line in text.splitlines()])
    # Limitahan ang magkakasunod na blank lines sa isa lang max
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def transpose_chord_token(chord, semitones):
    """
    Nag-t-transpose ng isang pirasong chord token (hal. C#m7 -> D#m7 o D/F# -> F/A)
    """
    if not chord:
        return chord
        
    # Kung ito ay isang slash chord (hal. D/F#), i-transpose ang magkabilang parte
    if '/' in chord:
        parts = chord.split('/')
        return '/'.join([transpose_chord_token(p, semitones) for p in parts])
        
    # Hanapin ang root note (hal. C, C#, Db)
    match = re.match(r'^([A-G][#b]?)', chord)
    if not match:
        return chord
        
    root = match.group(1)
    suffix = chord[len(root):] # kukunin ang mga 'm', '7', 'sus4', atbp.
    
    # 12-Semitone Chromatic Scale Wheel
    scale = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    flat_map = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#', 'E#': 'F', 'B#': 'C'}
    
    # I-normalize ang mga flat notes papuntang sharp equivalents
    normalized_root = flat_map.get(root, root)
    if normalized_root not in scale:
        return chord
        
    current_idx = scale.index(normalized_root)
    new_idx = (current_idx + semitones) % 12
    new_root = scale[new_idx]
    
    return f"{new_root}{suffix}"


def transpose_chords_text(text, semitones):
    """
    Ini-scan ang buong text sheet at pinapasa sa transposition algorithm
    ang mga tugmang chord structures gamit ang Regex.
    """
    if not text or semitones == 0:
        return text
        
    # Safe regex pattern para sa mga chords (umiwas sa pag-gawaw ng normal na lyrics text)
    chord_pattern = r'\b[A-G][#b]?(?:m|maj|min|dim|aug|sus|add|b5|#5)?(?:[245679]|11|13)?(?:\/[A-G][#b]?)?\b'
    
    def replace_match(match):
        return transpose_chord_token(match.group(0), semitones)
        
    return re.sub(chord_pattern, replace_match, text)


def calculate_semitones_diff(from_key, to_key):
    """
    Kinukwenta kung ilang semitones ang layo ng lumang key sa bagong key
    """
    scale = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    flat_map = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
    
    k1 = flat_map.get(from_key, from_key)
    k2 = flat_map.get(to_key, to_key)
    
    if k1 in scale and k2 in scale:
        return (scale.index(k2) - scale.index(k1)) % 12
    return 0


# =========================================================================
# 1. CORE LYRICS FETCHING ENGINE (AJAX Endpoint) - Clean 3-Engine Fallback
# =========================================================================
@login_required
def get_lyrics(request):
    title = request.GET.get('title', '').strip()
    artist = request.GET.get('artist', '').strip()

    if not title or not artist:
        return JsonResponse({'error': 'Title and Artist are required.'}, status=400)

    clean_title = re.sub(r'\s+', ' ', title)
    lyrics_found = False
    response_data = {'lyrics': 'Lyrics not found.'}

    # --- ENGINE 1: LRCLIB FUZZY SEARCH ---
    if not lyrics_found:
        try:
            print(f"[SYNCO LOG] [ENGINE 1] Trying LRCLIB Fuzzy for: {artist} - {clean_title}...")
            search_query = f"{artist} {clean_title}"
            lrclib_search_url = f"https://lrclib.net/api/search?q={requests.utils.quote(search_query)}"
            res = requests.get(lrclib_search_url, headers=BROWSER_HEADERS, timeout=5)
            
            if res.status_code == 200 and res.json():
                results = res.json()
                if isinstance(results, list) and len(results) > 0:
                    data = results[0]
                    
                    # 💡 FIX: Prioritize plain lyrics. Kung synced lang ang meron, burahin ang timestamps gamit ang regex.
                    lyrics_text = data.get('plainLyrics')
                    if not lyrics_text and data.get('syncedLyrics'):
                        # Tinatanggal ang mga [00:00.00] o [00:00] format
                        lyrics_text = re.sub(r'\[\d{2}:\d{2}(?:\.\d{2})?\]', '', data.get('syncedLyrics'))
                    
                    if lyrics_text:
                        response_data['lyrics'] = lyrics_text.strip()
                        lyrics_found = True
                        print("[SYNCO LOG] ✅ Success via LRCLIB Fuzzy Search (?q=).")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ LRCLIB Fuzzy Error: {e}")

    # --- ENGINE 2: LRCLIB EXACT GET ---
    if not lyrics_found:
        try:
            print(f"[SYNCO LOG] [ENGINE 2] Trying LRCLIB Exact...")
            lrclib_get_url = f"https://lrclib.net/api/get?artist_name={requests.utils.quote(artist)}&track_name={requests.utils.quote(clean_title)}"
            res = requests.get(lrclib_get_url, headers=BROWSER_HEADERS, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                
                # 💡 FIX: Ganun din dito para sa Exact Engine
                lyrics_text = data.get('plainLyrics')
                if not lyrics_text and data.get('syncedLyrics'):
                    lyrics_text = re.sub(r'\[\d{2}:\d{2}(?:\.\d{2})?\]', '', data.get('syncedLyrics'))
                    
                if lyrics_text:
                    response_data['lyrics'] = lyrics_text.strip()
                    lyrics_found = True
                    print("[SYNCO LOG] ✅ Success via LRCLIB Exact Search.")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ LRCLIB Exact Error: {e}")

    # --- ENGINE 3: LYRICS.OVH ---
    if not lyrics_found:
        try:
            print(f"[SYNCO LOG] [ENGINE 3] Trying Lyrics.ovh...")
            ovh_url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(clean_title)}"
            res = requests.get(ovh_url, headers=BROWSER_HEADERS, timeout=6)
            
            if res.status_code != 200 or not res.json().get('lyrics'):
                title_cased = clean_title.title()
                if title_cased != clean_title:
                    ovh_url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(title_cased)}"
                    res = requests.get(ovh_url, headers=BROWSER_HEADERS, timeout=6)

            if res.status_code == 200:
                data = res.json()
                lyrics_text = data.get('lyrics')
                if lyrics_text and len(lyrics_text.strip()) > 0:
                    response_data['lyrics'] = lyrics_text.strip()
                    lyrics_found = True
                    print("[SYNCO LOG] ✅ Success via Lyrics.ovh Engine!")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ Lyrics.ovh Error: {e}")

    return JsonResponse(response_data, status=200)


# =========================================================================
# 2. CHORDS & YOUTUBE AUTOMATION UTILITIES (ANTI-BLOCK BYPASS)
# =========================================================================






def fetch_chords_duckduckgo(title, artist):
    def slugify(text):
        text = text.lower()
        text = text.replace('&', 'and')
        text = re.sub(r'\(.*?\)', '', text)
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        return re.sub(r'[\s-]+', '-', text).strip('-')

    clean_artist = re.sub(r'\(.*?\)', '', artist).strip()
    clean_title = re.sub(r'\(.*?\)', '', title).strip()

    artist_slug = slugify(clean_artist)
    title_slug = slugify(clean_title)

    # 🚀 GUMAWA NG CLOUDSCRAPER INSTANCE (Para sa Local Machine mo)
    scraper = cloudscraper.create_scraper(
        browser={
            'browser': 'chrome',
            'platform': 'windows',
            'desktop': True
        }
    )

    # =========================================================================
    # 🎛️ HYBRID SWITCH SYSTEM (Local vs Render)
    # =========================================================================
    IS_RENDER = os.environ.get('RENDER') == 'true'
    
    # Mas ligtas kung i-aadd mo ang 'SCRAPER_API_KEY' sa Environment Variables ng Render Dashboard.
    # Kung hindi, palitan mo na lang muna ang string placeholder sa ibaba.
    SCRAPER_API_KEY = os.environ.get('SCRAPER_API_KEY', 'ILAGAY_DITO_ANG_SCRAPER_API_KEY_MO')

    def smart_get(url, timeout_secs=10):
        """
        Matalinong tagapamahala ng network requests. 
        Gumagamit ng cloudscraper sa local, at ScraperAPI naman kapag nasa Render.
        """
        if IS_RENDER:
            print(f"[SYNCO PROXY RUNTIME] Routing via ScraperAPI: {url}")
            proxy_url = 'http://api.scraperapi.com'
            payload = {'api_key': SCRAPER_API_KEY, 'url': url}
            return requests.get(proxy_url, params=payload, timeout=timeout_secs + 5)
        else:
            # Walang bawas sa proxy credits mo kapag nagte-test ka sa sarili mong PC
            return scraper.get(url, timeout=timeout_secs)

    # =========================================================================
    # 💡 STRATEGY 1: ULTIMATE GUITAR DIRECT JSON SEARCH (BEST FOR RENDER)
    # =========================================================================
    print("[SYNCO CHORD LOG] Strategy 1: Bypassing DDG via Ultimate Guitar Direct Search...")
    try:
        query = f"{clean_artist} {clean_title}"
        ug_search_url = f"https://www.ultimate-guitar.com/search.php?search_type=title&value={requests.utils.quote(query)}"
        
        # Ginamit ang smart_get para awtomatikong mag-switch
        res = smart_get(ug_search_url, timeout_secs=10)
        print(f"[SYNCO DEBUG] Strategy 1 Search Gateway Status: {res.status_code}")
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            store_div = soup.find("div", class_="js-store")
            
            if store_div:
                json_str = store_div.get("data-content") or store_div.string
                if json_str:
                    data = json.loads(json_str)
                    results = data.get("store", {}).get("page", {}).get("data", {}).get("results", [])
                    chord_results = [r for r in results if r.get("type") == "Chords"]
                    
                    if chord_results:
                        target_tab_url = chord_results[0].get("tab_url")
                        print(f"[SYNCO CHORD LOG] Found UG Target directly: {target_tab_url}")
                        
                        tab_res = smart_get(target_tab_url, timeout_secs=10)
                        print(f"[SYNCO DEBUG] Strategy 1 Tab Fetch Status: {tab_res.status_code}")
                        if tab_res.status_code == 200:
                            tab_soup = BeautifulSoup(tab_res.text, "html.parser")
                            tab_store = tab_soup.find("div", class_="js-store")
                            if tab_store:
                                tab_json = tab_store.get("data-content") or tab_store.string
                                if tab_json:
                                    tab_data = json.loads(tab_json)
                                    raw_chords = tab_data['store']['page']['data']['tab_view']['wiki_tab']['content']
                                    clean_text = raw_chords.replace('[ch]', '').replace('[/ch]', '').replace('[tab]', '').replace('[/tab]', '')
                                    print("[SYNCO CHORD LOG] ✅ BOOM! SUCCESS via Strategy 1!")
                                    return clean_chords_formatting(clean_text)
    except Exception as e:
        print(f"[SYNCO CHORD LOG] Strategy 1 UG bypass failed: {e}")

    # =========================================================================
    # 💡 STRATEGY 2: DIRECT GUESSING URLS (Fallback)
    # =========================================================================
    print("[SYNCO CHORD LOG] Strategy 2: Activating Direct URL Guessing...")
    direct_urls = [
        f"https://www.e-chords.com/chords/{artist_slug}/{title_slug}",
        f"https://www.tabs4acoustic.com/guitar-tabs/{artist_slug}-{title_slug}-chords.html",
        f"https://www.guitartabs.cc/tabs/{artist_slug}/{title_slug}_chords.htm",
    ]
    possible_selectors = ["pre", ".core-chords", "#chords_body", ".tab-content", ".content", "code", ".chord-wrapper"]
    
    for url in direct_urls:
        try:
            page = smart_get(url, timeout_secs=7)
            print(f"[SYNCO DEBUG] Strategy 2 Target: {url} | Status: {page.status_code}")
            if page.status_code == 200 and "chords" in page.text.lower():
                soup = BeautifulSoup(page.text, "html.parser")
                for sel in possible_selectors:
                    el = soup.select_one(sel)
                    if el:
                        text = el.get_text("\n")
                        if re.search(r"\b[A-G](m|maj|min|dim|aug|sus|7)?\b", text):
                            print(f"[SYNCO CHORD LOG] ✅ SUCCESS! Bypassed via Direct Guess: {url}")
                            return clean_chords_formatting(text)
        except Exception as e:
            print(f"[SYNCO CHORD LOG] Direct URL attempt failed for {url}: {e}")

    # =========================================================================
    # 💡 STRATEGY 3: DUCKDUCKGO SEARCH GATEWAY (Fallback 2)
    # =========================================================================
    query = f"{clean_artist} {clean_title} chords"
    print(f"[SYNCO CHORD LOG] Strategy 3: Deploying Open-Search Engine for: {query}...")
    
    search_gateways = [
        f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}",
        f"https://lite.duckduckgo.com/lite/?q={requests.utils.quote(query)}"
    ]
    
    scraped_links = []
    for gateway_url in search_gateways:
        try:
            res = smart_get(gateway_url, timeout_secs=8)
            print(f"[SYNCO DEBUG] Strategy 3 Gateway: {gateway_url} | Status: {res.status_code}")
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "html.parser")
                links = soup.select(".result__a") or soup.find_all("a", href=True)
                for link in links:
                    href = link.get("href", "")
                    decoded_href = requests.utils.unquote(href)
                    actual_url = None
                    if "uddg=" in decoded_href:
                        actual_url = decoded_href.split("uddg=")[1].split("&")[0]
                    elif "r.html?url=" in decoded_href:
                        actual_url = decoded_href.split("r.html?url=")[1].split("&")[0]
                    elif href.startswith("http"):
                        actual_url = href
                        
                    if actual_url:
                        actual_url_lower = actual_url.lower()
                        if any(site in actual_url_lower for site in ["ultimate-guitar.com", "e-chords.com", "guitartabs.cc", "tabs4acoustic", "chordie.com", "amchords.com"]):
                            if actual_url not in scraped_links:
                                scraped_links.append(actual_url)
                if scraped_links:
                    break
        except Exception as search_err:
            print(f"[SYNCO CHORD LOG] Gateway skipped: {search_err}")

    print(f"[SYNCO CHORD LOG] Search Engine extracted {len(scraped_links)} candidate targets.")

    for target_url in scraped_links[:4]:
        try:
            if "ultimate-guitar.com" in target_url:
                ug_page = smart_get(target_url, timeout_secs=8)
                print(f"[SYNCO DEBUG] Strategy 3 Dynamic Target Status: {ug_page.status_code}")
                if ug_page.status_code == 200:
                    ug_soup = BeautifulSoup(ug_page.text, "html.parser")
                    ug_store = ug_soup.select_one(".js-store") or ug_soup.find(class_="js-store")
                    if ug_store:
                        json_str = ug_store.get("data-content") or ug_store.string
                        if json_str:
                            data = json.loads(json_str)
                            raw_chords = data['store']['page']['data']['tab_view']['wiki_tab']['content']
                            clean_text = raw_chords.replace('[ch]', '').replace('[/ch]', '').replace('[tab]', '').replace('[/tab]', '')
                            return clean_chords_formatting(clean_text)
                continue

            page = smart_get(target_url, timeout_secs=7)
            print(f"[SYNCO DEBUG] Strategy 3 Standard Target Status: {page.status_code}")
            if page.status_code == 200:
                page_soup = BeautifulSoup(page.text, "html.parser")
                for sel in possible_selectors:
                    el = page_soup.select_one(sel)
                    if el:
                        text = el.get_text("\n")
                        if re.search(r"\b[A-G](m|maj|min|dim|aug|sus|7)?\b", text):
                            return clean_chords_formatting(text)
        except Exception as crawl_err:
            print(f"[SYNCO CHORD LOG] Skipping {target_url}: {crawl_err}")

    # =========================================================================
    # 💡 STRATEGY 4: CHORDIE FINAL RESORT
    # =========================================================================
    print(f"[SYNCO CHORD LOG] Strategy 4: Deploying Final Resort (Chordie Search)...")
    try:
        chordie_url = f"https://www.chordie.com/search.php?q={requests.utils.quote(clean_artist + ' ' + clean_title)}"
        res = smart_get(chordie_url, timeout_secs=7)
        print(f"[SYNCO DEBUG] Strategy 4 Search Status: {res.status_code}")
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "chord.pere" in href or "song.php" in href:
                    if not href.startswith("http"):
                        href = "https://www.chordie.com/" + href.lstrip("/")
                    page = smart_get(href, timeout_secs=6)
                    print(f"[SYNCO DEBUG] Strategy 4 Target Page Status: {page.status_code}")
                    if page.status_code == 200:
                        el = BeautifulSoup(page.text, "html.parser").select_one("pre")
                        if el:
                            text = el.get_text("\n")
                            if re.search(r"\b[A-G](m|maj|min|dim|aug|sus|7)?\b", text):
                                return clean_chords_formatting(text)
    except Exception:
        pass

    return None






def fetch_youtube_video_id(title, artist):
    api_key = os.getenv('YOUTUBE_API_KEY')
    query = f"{title} {artist} official audio"

    if api_key:
        try:
            print("[SYNCO LOG] Searching via YouTube API...")
            url = "https://www.googleapis.com/youtube/v3/search"
            params = {
                'part': 'snippet',
                'q': query,
                'key': api_key,
                'maxResults': 1,
                'type': 'video'
            }
            res = requests.get(url, params=params, timeout=5)
            if res.status_code == 200:
                data = res.json()
                items = data.get('items', [])
                if items:
                    return items[0]['id']['videoId']
            elif res.status_code == 403:
                print("⚠️ YouTube Quota Exceeded! Switching to DuckDuckGo Scraper...")
        except Exception as e:
            print(f"[YOUTUBE API ERROR] {e}")

    try:
        print("[SYNCO LOG] Scraping YouTube ID via DuckDuckGo...")
        ddg_url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query + ' site:youtube.com')}"
        res = requests.get(ddg_url, headers=BROWSER_HEADERS, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.select(".result__a")

        for link in links:
            href = link.get("href", "")
            decoded_href = requests.utils.unquote(href)

            if 'youtube.com/watch' in decoded_href:
                match = re.search(r'v=([^&#?]+)', decoded_href)
                if match:
                    return match.group(1)
            elif 'youtu.be/' in decoded_href:
                match = re.search(r'youtu\.be/([^&#?]+)', decoded_href)
                if match:
                    return match.group(1)
    except Exception as e:
        print(f"[YOUTUBE SCRAPE FALLBACK ERROR] {e}")

    return ""

@login_required
def api_fetch_chords(request):
    title = request.GET.get('title', '').strip()
    artist = request.GET.get('artist', '').strip()

    if not title or not artist:
        return JsonResponse({'error': 'Title and Artist are required.'}, status=400)

    chords_data = fetch_chords_duckduckgo(title, artist)
    youtube_id = fetch_youtube_video_id(title, artist)

    return JsonResponse({
        'chords': chords_data or "Chords could not be auto-extracted. Please find manually.",
        'youtube_id': youtube_id
    })


# =========================================================================
# 2.5. LIVE TRANSPOSE AJAX ENDPOINT
# =========================================================================
@login_required
def transpose_song_api(request):
    """
    Tumatanggap ng chords body text, kasalukuyang Key, at Target Key mula sa AJAX.
    Ibabato pabalik ang bago at kalkuladong chords nang hindi nire-refresh ang pahina.
    """
    chords_text = request.POST.get('chords', '') or request.GET.get('chords', '')
    from_key = request.GET.get('from_key', '').strip().upper()
    to_key = request.GET.get('to_key', '').strip().upper()
    
    semitones = request.GET.get('semitones', None)
    
    if semitones is not None:
        try:
            semitones_diff = int(semitones)
        except ValueError:
            semitones_diff = 0
    else:
        if not from_key or not to_key:
            return JsonResponse({'error': 'Kailangan ng from_key at to_key o semitones parameter.'}, status=400)
        semitones_diff = calculate_semitones_diff(from_key, to_key)
        
    transposed_result = transpose_chords_text(chords_text, semitones_diff)
    
    return JsonResponse({
        'success': True,
        'transposed_chords': transposed_result,
        'semitones_shifted': semitones_diff
    })


# =========================================================================
# 3. STANDARD CRUD / PAGE VIEWS
# =========================================================================

@login_required
def song_list(request):
    songs = Song.objects.all().order_by('-id')
    return render(request, 'songs/song_list.html', {'songs': songs})


@login_required
def song_detail(request, pk):
    song = get_object_or_404(Song, id=pk)
    if song.chords:
        song.chords = clean_chords_formatting(song.chords)
    return render(request, 'songs/song_detail.html', {'song': song})


@login_required
def add_song(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        artist = request.POST.get('artist')
        lyrics = request.POST.get('lyrics')
        chords = request.POST.get('chords')
        youtube_id = request.POST.get('youtube_id', '')

        if title and artist:
            formatted_chords = clean_chords_formatting(chords) if chords else ""
            
            Song.objects.create(
                title=title, 
                artist=artist, 
                lyrics=lyrics, 
                chords=formatted_chords, 
                youtube_id=youtube_id
            )
            messages.success(request, "Song successfully added!")
            return redirect('song_list')
        else:
            messages.error(request, "Please fill out all required fields.")
    return render(request, 'songs/add_song.html')


@login_required
def song_delete(request, pk):
    song = get_object_or_404(Song, id=pk)
    if request.method == 'POST':
        song.delete()
        messages.success(request, "Song successfully deleted!")
        return redirect('song_list')
    return render(request, 'songs/song_confirm_delete.html', {'song': song})


# =========================================================================
# CLEAN ALIASES (MATCHING urls.py)
# =========================================================================

song_list_view = song_list
song_detail_view = song_detail
song_create_view = add_song
song_delete_view = song_delete
get_lyrics_api = get_lyrics
fetch_chords_api = api_fetch_chords
transpose_api = transpose_song_api