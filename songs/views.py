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
# 1. CORE LYRICS FETCHING ENGINE (AJAX Endpoint) - Clean 3-Engine Fallback
# =========================================================================
def get_lyrics(request):
    """
    Endpoint na tinatawag ng AJAX para kumuha ng lyrics gamit ang 3-Engine Fallback system.
    """
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
# 2. CHORDS & YOUTUBE AUTOMATION UTILITIES
# =========================================================================

def fetch_chords_duckduckgo(title, artist):
    """
    Scraper para kumuha ng chords mula sa pinakaunang resulta sa DuckDuckGo.
    """
    try:
        query = f"{title} {artist} chords"
        url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query)}"

        res = requests.get(url, headers=BROWSER_HEADERS, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")

        links = soup.select(".result__a")
        if not links:
            return None

        first_link = links[0]["href"]

        page = requests.get(first_link, headers=BROWSER_HEADERS, timeout=8)
        page_soup = BeautifulSoup(page.text, "html.parser")

        possible_selectors = [
            ".chords",
            ".lyrics",
            "pre",
            ".content",
            ".tab-content"
        ]

        for sel in possible_selectors:
            el = page_soup.select_one(sel)
            if el:
                text = el.get_text("\n")
                if re.search(r"\b[A-G](m|maj|min|dim|aug|sus|7)?\b", text):
                    return text.strip()

        return None
    except Exception as e:
        print(f"[CHORD ENGINE ERROR] {e}")
        return None


def fetch_youtube_video_id(title, artist):
    """
    Plan A: Hahanap gamit ang opisyal na YouTube API.
    Plan B: Fallback gamit ang DuckDuckGo HTML parsing (May URL Decode Fix para sa Regex).
    """
    api_key = os.getenv('YOUTUBE_API_KEY')
    query = f"{title} {artist} official audio"

    # --- PLAN A: OFFICIAL YOUTUBE API ---
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

    # --- PLAN B: DUCKDUCKGO SCRAPER FALLBACK (FIXED!) ---
    try:
        print("[SYNCO LOG] Scraping YouTube ID via DuckDuckGo...")
        ddg_url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query + ' site:youtube.com')}"
        res = requests.get(ddg_url, headers=BROWSER_HEADERS, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")
        links = soup.select(".result__a")

        for link in links:
            href = link.get("href", "")
            
            # CRITICAL FIX: I-decode ang DDG redirect link para lumabas ang malinis na 'v=VIDEO_ID'
            decoded_href = requests.utils.unquote(href)
            print(f"[SYNCO LOG] Inspected Link: {decoded_href}")

            if 'youtube.com/watch' in decoded_href:
                match = re.search(r'v=([^&#?]+)', decoded_href)
                if match:
                    video_id = match.group(1)
                    print(f"[SYNCO LOG] ✅ Successfully extracted YT ID: {video_id}")
                    return video_id
            elif 'youtu.be/' in decoded_href:
                match = re.search(r'youtu\.be/([^&#?]+)', decoded_href)
                if match:
                    video_id = match.group(1)
                    print(f"[SYNCO LOG] ✅ Successfully extracted YT ID: {video_id}")
                    return video_id
    except Exception as e:
        print(f"[YOUTUBE SCRAPE FALLBACK ERROR] {e}")

    return ""


def api_fetch_chords(request):
    """
    AJAX endpoint na tinatawag ng frontend para sabay na i-fetch ang Chords at YT Video ID.
    """
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
# 3. STANDARD CRUD / PAGE VIEWS (Naka-align na sa 'pk' parameter)
# =========================================================================

def song_list(request):
    songs = Song.objects.all().order_by('-id')
    return render(request, 'songs/song_list.html', {'songs': songs})


def song_detail(request, pk):
    song = get_object_or_404(Song, id=pk)
    return render(request, 'songs/song_detail.html', {'song': song})


def add_song(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        artist = request.POST.get('artist')
        lyrics = request.POST.get('lyrics')
        youtube_id = request.POST.get('youtube_id', '')

        if title and artist:
            Song.objects.create(title=title, artist=artist, lyrics=lyrics, youtube_id=youtube_id)
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
# 4. EXACT ALIAS BRIDGE (Sinasalo nito ang URLs mo)
# =========================================================================
song_list_view = song_list
song_detail_view = song_detail
song_create_view = add_song       
song_delete_view = song_delete    
get_lyrics_api = get_lyrics       
fetch_chords_api = api_fetch_chords  # <--- Ito ang tulay para sa chords at video automation!