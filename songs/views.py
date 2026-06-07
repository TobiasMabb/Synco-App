import re
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import Song  # Siguraduhing tugma sa pangalan ng iyong Model (singular)
from bs4 import BeautifulSoup
import re
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
# 2. STANDARD CRUD / PAGE VIEWS (Naka-align na sa 'pk' parameter ng URLs mo)
# =========================================================================

def song_list(request):
    songs = Song.objects.all().order_by('-id')
    return render(request, 'songs/song_list.html', {'songs': songs})


def song_detail(request, pk):  # <-- 'pk' ang ginamit para swak sa urls.py mo
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


def song_delete(request, pk):  # <-- Ibinaba rin ang delete function mo dito
    song = get_object_or_404(Song, id=pk)
    if request.method == 'POST':
        song.delete()
        messages.success(request, "Song successfully deleted!")
        return redirect('song_list')
    return render(request, 'songs/song_confirm_delete.html', {'song': song})



def fetch_chords_duckduckgo(title, artist):
    try:
        query = f"{title} {artist} chords"
        url = f"https://duckduckgo.com/html/?q={requests.utils.quote(query)}"

        res = requests.get(url, headers=BROWSER_HEADERS, timeout=8)
        soup = BeautifulSoup(res.text, "html.parser")

        # Get first result link
        links = soup.select(".result__a")

        if not links:
            return None

        first_link = links[0]["href"]

        # Follow result page
        page = requests.get(first_link, headers=BROWSER_HEADERS, timeout=8)
        page_soup = BeautifulSoup(page.text, "html.parser")

        # Try common chord containers
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
                
                # quick filter: must contain chord-like patterns
                if re.search(r"\b[A-G](m|maj|min|dim|aug|sus|7)?\b", text):
                    return text.strip()

        return None

    except Exception as e:
        print(f"[CHORD ENGINE ERROR] {e}")
        return None


# =========================================================================
# 3. EXACT ALIAS BRIDGE (Sinasalo nito ang synco/urls.py at songs/urls.py)
# =========================================================================
song_list_view = song_list
song_detail_view = song_detail
song_create_view = add_song       # <--- Heto ang hinahanap ng songs/urls.py mo!
song_delete_view = song_delete    # <--- Para sa delete path mo
get_lyrics_api = get_lyrics       # <--- Para sa AJAX get-lyrics path mo