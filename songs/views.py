import os
import re
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import Song  # Siguraduhing tugma sa pangalan ng iyong Model (singular)
from bs4 import BeautifulSoup

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
            lrclib_search_url = f"https://lrclib.net/api/search?artist={requests.utils.quote(artist)}&track={requests.utils.quote(clean_title)}"
            res = requests.get(lrclib_search_url, headers=BROWSER_HEADERS, timeout=5)
            
            if res.status_code == 200 and res.json():
                data = res.json()[0]
                lyrics_text = data.get('syncedLyrics') or data.get('plainLyrics')
                if lyrics_text:
                    response_data['lyrics'] = lyrics_text.strip()
                    lyrics_found = True
                    print("[SYNCO LOG] ✅ Success via LRCLIB Fuzzy Search.")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ LRCLIB Fuzzy Error: {e}")

    # --- ENGINE 2: LRCLIB EXACT GET ---
    if not lyrics_found:
        try:
            print(f"[SYNCO LOG] [ENGINE 2] Trying LRCLIB Exact...")
            lrclib_get_url = f"https://lrclib.net/api/get?artist={requests.utils.quote(artist)}&track={requests.utils.quote(clean_title)}"
            res = requests.get(lrclib_get_url, headers=BROWSER_HEADERS, timeout=5)
            
            if res.status_code == 200:
                data = res.json()
                lyrics_text = data.get('syncedLyrics') or data.get('plainLyrics')
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
        text = re.sub(r'[^a-z0-9\s-]', '', text)
        return re.sub(r'[\s-]+', '-', text).strip('-')

    artist_slug = slugify(artist)
    title_slug = slugify(title)
    
    direct_urls = [
        f"https://www.e-chords.com/chords/{artist_slug}/{title_slug}",
        f"https://www.tabs4acoustic.com/guitar-tabs/{artist_slug}-{title_slug}-chords.html"
    ]
    
    possible_selectors = ["pre", ".core-chords", "#chords_body", ".tab-content", ".content", "code"]
    
    print(f"[SYNCO CHORD LOG] Strategy 1: Activating Direct URL Guessing...")
    for url in direct_urls:
        try:
            print(f"[SYNCO CHORD LOG] Target: {url}")
            page = requests.get(url, headers=BROWSER_HEADERS, timeout=5)
            if page.status_code == 200 and "chords" in page.text.lower():
                soup = BeautifulSoup(page.text, "html.parser")
                for sel in possible_selectors:
                    el = soup.select_one(sel)
                    if el:
                        text = el.get_text("\n")
                        if re.search(r"\b[A-G](m|maj|min|dim|aug|sus|7)?\b", text):
                            print(f"[SYNCO CHORD LOG] ✅ SUCCESS! Bypassed search blocks via: {url}")
                            return clean_chords_formatting(text) # 👈 GINAMITAN NG FORMAT CLEANER ENGINE
        except Exception as e:
            print(f"[SYNCO CHORD LOG] Direct URL attempt failed for {url}: {e}")

    print(f"[SYNCO CHORD LOG] Strategy 2: Falling back to Chordie Internal Search Engine...")
    try:
        query = f"{artist} {title}"
        chordie_url = f"https://www.chordie.com/search.php?q={requests.utils.quote(query)}"
        res = requests.get(chordie_url, headers=BROWSER_HEADERS, timeout=6)
        
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            candidate_links = []
            
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "chord.pere" in href or "song.php" in href:
                    if not href.startswith("http"):
                        href = "https://www.chordie.com/" + href.lstrip("/")
                    if href not in candidate_links:
                        candidate_links.append(href)
            
            for target_url in candidate_links[:3]:
                print(f"[SYNCO CHORD LOG] Scraping Chordie candidate: {target_url}")
                page = requests.get(target_url, headers=BROWSER_HEADERS, timeout=5)
                if page.status_code == 200:
                    page_soup = BeautifulSoup(page.text, "html.parser")
                    el = page_soup.select_one("pre")
                    if el:
                        text = el.get_text("\n")
                        if re.search(r"\b[A-G](m|maj|min|dim|aug|sus|7)?\b", text):
                            print(f"[SYNCO CHORD LOG] ✅ SUCCESS! Extracted from Chordie: {target_url}")
                            return clean_chords_formatting(text) # 👈 GINAMITAN NG FORMAT CLEANER ENGINE
    except Exception as e:
        print(f"[SYNCO CHORD LOG] Chordie Engine system exception: {e}")

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
# 2.5. LIVE TRANSPOSE AJAX ENDPOINT (Bago at magagamit sa Frontend Buttons)
# =========================================================================
def transpose_song_api(request):
    """
    Tumatanggap ng chords body text, kasalukuyang Key, at Target Key mula sa AJAX.
    Ibabato pabalik ang bago at kalkuladong chords nang hindi nire-refresh ang pahina.
    """
    chords_text = request.POST.get('chords', '') or request.GET.get('chords', '')
    from_key = request.GET.get('from_key', '').strip().upper()
    to_key = request.GET.get('to_key', '').strip().upper()
    
    # Pwede ring direktang semitones shift ang ipadala (hal. +2 o -1)
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

def song_list(request):
    songs = Song.objects.all().order_by('-id')
    return render(request, 'songs/song_list.html', {'songs': songs})


def song_detail(request, pk):
    song = get_object_or_404(Song, id=pk)
    # Awtomatikong nililinis ang pormat kapag binuksan ang detalye para siguradong plantsado ang alignment
    if song.chords:
        song.chords = clean_chords_formatting(song.chords)
    return render(request, 'songs/song_detail.html', {'song': song})


def add_song(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        artist = request.POST.get('artist')
        lyrics = request.POST.get('lyrics')
        chords = request.POST.get('chords')
        youtube_id = request.POST.get('youtube_id', '')

        if title and artist:
            # Nililinis ang chords bago i-commit sa database
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
transpose_api = transpose_song_api  # 👈 I-expose ang bagong transpose utility sa iyong router