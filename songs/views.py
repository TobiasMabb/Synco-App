import os
import re
import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Song

# --- PRODUCTION DETECTION ---
IS_PYTHONANYWHERE = 'PYTHONANYWHERE_SITE' in os.environ
PROXY_URL = 'http://proxy.server:3128'

# Gagamitin lang natin ang Genius sa Local development para hindi sumasabog sa Render
IS_LOCAL = not ('RENDER' in os.environ or IS_PYTHONANYWHERE)

# Shared Browser Headers para magpanggap na totoong Chrome Browser
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 🛠️ I-PASTE MO DITO ANG NAKUHA MONG YOUTUBE API KEY MULA KAY GOOGLE
YOUTUBE_API_KEY = "AIzaSyA4BiwzKN56jYWIH9BI5DzmCqBNDK9snGk"

def song_list_view(request):
    songs = Song.objects.all().order_by('-created_at')
    return render(request, 'songs/song_list.html', {'songs': songs})

def song_create_view(request):
    if request.method == "POST":
        title = request.POST.get('title')
        artist = request.POST.get('artist')
        lyrics = request.POST.get('lyrics', '')
        chords = request.POST.get('chords', '')
        youtube_id = request.POST.get('youtube_id', '')
        
        Song.objects.create(title=title, artist=artist, lyrics=lyrics, chords=chords, youtube_id=youtube_id)
        return redirect('song_list')
    return render(request, 'songs/add_song.html')

def get_lyrics_api(request):
    title = request.GET.get('title', '').strip()
    artist = request.GET.get('artist', '').strip()
    
    if not title or not artist:
        return JsonResponse({'lyrics': 'Please enter both Title and Artist.', 'youtube_id': ''})

    response_data = {
        'lyrics': "⚠️ Lyrics not found in database.\n\nPlease copy and paste the lyrics manually.",
        'youtube_id': ''
    }

    # Linisin ang pamagat sa mga brackets (e.g. "Song (Live)" -> "Song")
    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title).strip()
    lyrics_found = False
    proxies = {'http': PROXY_URL, 'https': PROXY_URL} if IS_PYTHONANYWHERE else None

    # =========================================================================
    # --- STRATEGY A: LRCLIB FUZZY SEARCH (Pinakamataas ang chance sa Render) ---
    # =========================================================================
    try:
        print(f"[SYNCO LOG] Fetching lyrics for: {artist} - {clean_title} via LRCLIB...")
        lrclib_url = "https://lrclib.net/api/search"
        params = {'q': f"{artist} {clean_title}"}
        
        res = requests.get(lrclib_url, params=params, headers=BROWSER_HEADERS, proxies=proxies, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                # Kuhanin ang pinaka-unang match
                chosen_song = data[0]
                lyrics_text = chosen_song.get('plainLyrics') or chosen_song.get('syncedLyrics')
                
                if lyrics_text:
                    if not chosen_song.get('plainLyrics') and chosen_song.get('syncedLyrics'):
                        lyrics_text = re.sub(r'\[\d+:\d+[^\]]*\]', '', lyrics_text).strip()
                    
                    response_data['lyrics'] = lyrics_text
                    lyrics_found = True
                    print("[SYNCO LOG] ✅ Success! Lyrics fetched via LRCLIB Fuzzy Search.")
    except Exception as e:
        print(f"[SYNCO LOG] ❌ LRCLIB Fuzzy Search Error: {e}")

    # =========================================================================
    # --- STRATEGY B: LRCLIB EXACT SEARCH (Kung sakaling sumablay ang Fuzzy) ---
    # =========================================================================
    if not lyrics_found:
        try:
            print("[SYNCO LOG] Retrying via LRCLIB Exact Search...")
            lrclib_url = "https://lrclib.net/api/search"
            params = {'track_name': clean_title, 'artist_name': artist}
            
            res = requests.get(lrclib_url, params=params, headers=BROWSER_HEADERS, proxies=proxies, timeout=10)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0:
                    chosen_song = data[0]
                    lyrics_text = chosen_song.get('plainLyrics') or chosen_song.get('syncedLyrics')
                    if lyrics_text:
                        if not chosen_song.get('plainLyrics') and chosen_song.get('syncedLyrics'):
                            lyrics_text = re.sub(r'\[\d+:\d+[^\]]*\]', '', lyrics_text).strip()
                        response_data['lyrics'] = lyrics_text
                        lyrics_found = True
                        print("[SYNCO LOG] ✅ Success! Lyrics fetched via LRCLIB Exact Search.")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ LRCLIB Exact Search Error: {e}")

    # =========================================================================
    # --- STRATEGY C: LOCAL GENIUS FALLBACK (Gagana lang kapag nasa PC mo) ---
    # =========================================================================
    if not lyrics_found and IS_LOCAL:
        try:
            print("[SYNCO LOG] Local environment detected. Trying Genius Client...")
            import lyricsgenius
            GENIUS_TOKEN = "Lwh7dOi2bTY2TCdAQpe-g5tCOwu3YoTtaPK-e9LWPVCjc8OZf40ro4pIIPb0_Sth"
            genius_client = lyricsgenius.Genius(GENIUS_TOKEN, timeout=10, retries=2)
            genius_client.headers = BROWSER_HEADERS
            genius_client.verbose = False
            genius_client.remove_section_headers = True
            
            song = genius_client.search_song(title, artist)
            if song and song.lyrics:
                clean_lyrics = song.lyrics.replace(f"{song.title} Lyrics", "", 1).strip()
                if clean_lyrics.endswith("Embed"):
                    clean_lyrics = clean_lyrics[:-5].strip()
                clean_lyrics = re.sub(r'\d+$', '', clean_lyrics).strip()
                response_data['lyrics'] = clean_lyrics
                lyrics_found = True
                print("[SYNCO LOG] ✅ Success! Lyrics fetched via Genius (Local Fallback).")
        except Exception as e:
            print(f"[SYNCO LOG] ❌ Genius Local Fallback Error: {e}")

    # =========================================================================
    # --- HAKBANG B: KUKUNIN ANG YOUTUBE VIDEO ID ---
    # =========================================================================
    try:
        if YOUTUBE_API_KEY:
            url = "https://www.googleapis.com/youtube/v3/search"
            search_query = f"{artist} {title} lyrics"
            
            params = {
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'videoEmbeddable': 'true',
                'videoSyndicated': 'true',
                'key': YOUTUBE_API_KEY,
                'maxResults': 5
            }
            
            yt_res = requests.get(url, params=params, proxies=proxies, timeout=10).json()
            
            if 'items' in yt_res and len(yt_res['items']) > 0:
                selected_video_id = None
                for item in yt_res['items']:
                    channel_title = item['snippet'].get('channelTitle', '')
                    if "Topic" not in channel_title:
                        selected_video_id = item['id']['videoId']
                        break
                if not selected_video_id:
                    selected_video_id = yt_res['items'][0]['id']['videoId']
                    
                response_data['youtube_id'] = selected_video_id
                print("[SYNCO LOG] ✅ Success! YouTube ID fetched.")
                
    except Exception as e:
        print(f"[SYNCO LOG] ❌ YouTube Fetch Error: {e}")
        
    return JsonResponse(response_data)  

def song_detail_view(request, pk):
    return render(request, 'songs/song_detail.html', {'song': get_object_or_404(Song, pk=pk)})

def song_delete_view(request, pk):
    get_object_or_404(Song, pk=pk).delete()
    return redirect('song_list')