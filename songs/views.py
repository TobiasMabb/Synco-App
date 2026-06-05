import re
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib import messages
from .models import Song  # Siguraduhing tugma sa pangalan ng iyong Model

# Common Headers para sa mga out-bound API requests
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

# =========================================================================
# 1. CORE LYRICS FETCHING ENGINE (AJAX Endpoint)
# =========================================================================
def get_lyrics(request):
    """
    Endpoint na tinatawag ng AJAX para kumuha ng lyrics gamit ang 4-Engine Fallback system.
    URL: /songs/get-lyrics/?title=...&artist=...
    """
    title = request.GET.get('title', '').strip()
    artist = request.GET.get('artist', '').strip()

    if not title or not artist:
        return JsonResponse({'error': 'Title and Artist are required.'}, status=400)

    # Linisin ang title (tanggalin ang extra spaces)
    clean_title = re.sub(r'\s+', ' ', title)
    
    lyrics_found = False
    response_data = {'lyrics': 'Lyrics not found.'}

    # =========================================================================
    # --- ENGINE 1: LRCLIB FUZZY SEARCH ---
    # =========================================================================
    if not lyrics_found:
        try:
            print(f"[SYNCO LOG] [ENGINE 1] Trying LRCLIB Fuzzy for: {artist} - {clean_title}...")
            lrclib_search_url = f"https://lrclib.net/api/search?artist={requests.utils.quote(artist)}&track={requests.utils.quote(clean_title)}"
            res = requests.get(lrclib_search_url, headers=BROWSER_HEADERS, timeout=5)
            
            if res.status_code == 200 and res.json():
                data = res.json()[0]  # Kuhanin ang pinaka-unang match
                lyrics_text = data.get('syncedLyrics') or data.get('plainLyrics')
                if lyrics_text:
                    response_data['lyrics'] = lyrics_text.strip()
                    lyrics_found = True
                    print("[SYNCO LOG] ✅ Success! Lyrics fetched via LRCLIB Fuzzy Search.")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ LRCLIB Fuzzy Error: {e}")

    # =========================================================================
    # --- ENGINE 2: LRCLIB EXACT GET ---
    # =========================================================================
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
                    print("[SYNCO LOG] ✅ Success! Lyrics fetched via LRCLIB Exact Search.")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ LRCLIB Exact Error: {e}")

    # =========================================================================
    # --- ENGINE 3: LYRICS.OVH (May Case-Insensitive Retry) ---
    # =========================================================================
    if not lyrics_found:
        try:
            print(f"[SYNCO LOG] [ENGINE 3] Trying Lyrics.ovh for: {artist} - {clean_title}...")
            ovh_url = f"https://api.lyrics.ovh/v1/{requests.utils.quote(artist)}/{requests.utils.quote(clean_title)}"
            res = requests.get(ovh_url, headers=BROWSER_HEADERS, timeout=6)
            
            # Kapag walang nahanap (tulad ng case-sensitivity bug sa "Good news")
            if res.status_code != 200 or not res.json().get('lyrics'):
                title_cased = clean_title.title()  # Gagawing Proper Case ("Good News")
                if title_cased != clean_title:
                    print(f"[SYNCO LOG] [ENGINE 3 Retry] Trying Title Case: {artist} - {title_cased}...")
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

    # =========================================================================
    # --- ENGINE 4: GENIUS FALLBACK (Via Free ScraperAPI Proxy) ---
    # =========================================================================
    if not lyrics_found:
        try:
            print("[SYNCO LOG] [ENGINE 4] Routing Genius through ScraperAPI Proxy...")
            import lyricsgenius
            
            GENIUS_TOKEN = "Lwh7dOi2bTY2TCdAQpe-g5tCOwu3YoTtaPK-e9LWPVCjc8OZf40ro4pIIPb0_Sth"
            genius_client = lyricsgenius.Genius(GENIUS_TOKEN, timeout=15, retries=1)
            
            # 🛠️ IPALIT DITO ANG IYONG SCRAPERAPI KEY MULA SA KANILANG DASHBOARD
            SCRAPERAPI_KEY = "3548bf98fe767c4f7b81b3b0aac75102" 
            
            # Ipadaan ang setup ng Genius session sa proxies ng ScraperAPI para malusutan si Cloudflare
            scraper_proxy = f"http://scraperapi:{SCRAPERAPI_KEY}@proxy-server.scraperapi.com:8001"
            genius_client.session.proxies = {
                'http': scraper_proxy,
                'https': scraper_proxy
            }
            
            genius_client.headers = BROWSER_HEADERS
            genius_client.verbose = False
            genius_client.remove_section_headers = True
            
            song = genius_client.search_song(clean_title, artist)
            if song and song.lyrics:
                clean_lyrics = song.lyrics.replace(f"{song.title} Lyrics", "", 1).strip()
                if clean_lyrics.endswith("Embed"):
                    clean_lyrics = clean_lyrics[:-5].strip()
                clean_lyrics = re.sub(r'\d+$', '', clean_lyrics).strip()
                
                response_data['lyrics'] = clean_lyrics
                lyrics_found = True
                print("[SYNCO LOG] ✅ Success via Genius + ScraperAPI Proxy!")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ Genius Proxy Error: {e}")

    # Isabay na rin ang YouTube Fetch Success Confirmation log gaya ng dati mong format
    if lyrics_found:
        print("[SYNCO LOG] ✅ Success! YouTube ID fetched.")
        return JsonResponse(response_data, status=200)
    else:
        print("[SYNCO LOG] ❌ All lyric engines failed to find lyrics.")
        return JsonResponse(response_data, status=200)


# =========================================================================
# 2. STANDARD CRUD / PAGE VIEWS
# =========================================================================

def song_list(request):
    """
    URL: /songs/
    Nagpapakita ng lahat ng listahan ng kanta.
    """
    songs = Song.objects.all().order_by('-id')
    return render(request, 'songs/song_list.html', {'songs': songs})


def song_detail(request, song_id):
    """
    URL: /songs/<int:song_id>/
    Nagpapakita ng detalye at lyrics ng isang partikular na kanta.
    """
    song = get_object_or_404(Song, id=song_id)
    return render(request, 'songs/song_detail.html', {'song': song})


def song_add(request):
    """
    URL: /songs/add/
    Nagdadagdag ng bagong kanta sa database.
    """
    if request.method == 'POST':
        title = request.POST.get('title')
        artist = request.POST.get('artist')
        lyrics = request.POST.get('lyrics')
        youtube_id = request.POST.get('youtube_id', '') # Kung may YouTube link integration ka

        if title and artist:
            # I-save ang kanta sa database
            Song.objects.create(
                title=title,
                artist=artist,
                lyrics=lyrics,
                youtube_id=youtube_id
            )
            messages.success(request, "Song successfully added!")
            return redirect('song_list') # Mag-re-redirect (302) pabalik sa /songs/ listahan
        else:
            messages.error(request, "Please fill out all required fields.")

    return render(request, 'songs/song_add.html')