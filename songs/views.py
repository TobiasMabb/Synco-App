import os
import re
import requests
import lyricsgenius
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Song

# --- PRODUCTION PROXY DETECTION ---
IS_PYTHONANYWHERE = 'PYTHONANYWHERE_SITE' in os.environ
PROXY_URL = 'http://proxy.server:3128'

# Mas ligtas kung kukunin sa Render Environment, pero may fallback dito sa hardcoded token mo
GENIUS_TOKEN = os.environ.get("GENIUS_ACCESS_TOKEN", "Lwh7dOi2bTY2TCdAQpe-g5tCOwu3YoTtaPK-e9LWPVCjc8OZf40ro4pIIPb0_Sth")

# Initialize Genius client na may kasamang lakas sa timeout at retries para sa Render Free Tier
genius = lyricsgenius.Genius(GENIUS_TOKEN, timeout=15, retries=3)

# Magpanggap na totoong Chrome Browser para kung sakaling makalusot kay Cloudflare ng Genius
genius.headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# Tinatanggal ang mga [Chorus], [Verse 1] headers para malinis ang lyrics na papasok sa db niyo
genius.remove_section_headers = True

# Properly configure the proxy to its session parameters if on production
if IS_PYTHONANYWHERE:
    genius.proxies = {'http': PROXY_URL, 'https': PROXY_URL}

# Itatago nito ang mga technical logs sa terminal para malinis tignan
genius.verbose = False 

# 🛠️ I-PASTE MO DITO ANG NAKUHA MONG YOUTUBE API KEY KANINA MULA KAY GOOGLE
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
        youtube_id = request.POST.get('youtube_id', '')  # Bagong hila mula sa form
        
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

    # Linisin ng konti ang pamagat (tanggalin ang mga extra brackets tulad ng [Live] o (Official))
    clean_title = re.sub(r'\(.*?\)|\[.*?\]', '', title).strip()
    lyrics_found = False

    # =========================================================================
    # --- ENGINE 1: SUBUKAN MUNA ANG LRCLIB (Hosting-Friendly, 100% GUMAGANA SA RENDER) ---
    # =========================================================================
    try:
        lrclib_url = "https://lrclib.net/api/search"
        params = {'track_name': clean_title, 'artist_name': artist}
        proxies = {'http': PROXY_URL, 'https': PROXY_URL} if IS_PYTHONANYWHERE else None
        
        res = requests.get(lrclib_url, params=params, proxies=proxies, timeout=8)
        if res.status_code == 200:
            data = res.json()
            if data and len(data) > 0:
                chosen_song = data[0]
                # Kumuha ng plain text lyrics; kung walang plain, gamitin ang synced lyrics
                lyrics_text = chosen_song.get('plainLyrics') or chosen_song.get('syncedLyrics')
                
                if lyrics_text:
                    # Kung synced lyrics ang nakuha, linisin at tanggalin ang mga timestamps na tulad ng [00:12.34]
                    if not chosen_song.get('plainLyrics') and chosen_song.get('syncedLyrics'):
                        lyrics_text = re.sub(r'\[\d+:\d+[^\]]*\]', '', lyrics_text).strip()
                    
                    response_data['lyrics'] = lyrics_text
                    lyrics_found = True
                    print("✅ Lyrics successfully fetched via LRCLIB engine!")
    except Exception as e:
        print(f"LRCLIB Engine Error: {e}")

    # =========================================================================
    # --- ENGINE 2: FALLBACK TO GENIUS (Kung sakaling walang nahanap sa LRCLIB) ---
    # =========================================================================
    if not lyrics_found:
        try:
            song = genius.search_song(title, artist)
            if song and song.lyrics:
                clean_lyrics = song.lyrics.replace(f"{song.title} Lyrics", "", 1).strip()
                if clean_lyrics.endswith("Embed"):
                    clean_lyrics = clean_lyrics[:-5].strip()
                clean_lyrics = re.sub(r'\d+$', '', clean_lyrics).strip()
                response_data['lyrics'] = clean_lyrics
                lyrics_found = True
                print("✅ Lyrics successfully fetched via Genius engine!")
        except Exception as e:
            print(f"Genius Engine Fallback Error (Blocked or Not Found): {e}")

    # =========================================================================
    # --- HAKBANG B: KUKUNIN ANG YOUTUBE VIDEO ID ---
    # =========================================================================
    try:
        if YOUTUBE_API_KEY and YOUTUBE_API_KEY != "I-PASTE_DITO_YUNG_AIzaSy_KEY_MO":
            url = "https://www.googleapis.com/youtube/v3/search"
            search_query = f"{artist} {title} lyrics"
            
            params = {
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'videoEmbeddable': 'true',   # Dapat pwedeng i-embed sa code
                'videoSyndicated': 'true',   # Dapat pwedeng i-play sa labas ng youtube.com
                'key': YOUTUBE_API_KEY,
                'maxResults': 5
            }
            
            proxies = {'http': PROXY_URL, 'https': PROXY_URL} if IS_PYTHONANYWHERE else None
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
                
    except Exception as e:
        print(f"YouTube Fetch Error: {e}")
        
    return JsonResponse(response_data)  

def song_detail_view(request, pk):
    return render(request, 'songs/song_detail.html', {'song': get_object_or_404(Song, pk=pk)})

def song_delete_view(request, pk):
    get_object_or_404(Song, pk=pk).delete()
    return redirect('song_list')