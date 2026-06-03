import os
import re
import requests
import lyricsgenius
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Song

# --- PRODUCTION PROXY DETECTION ---
# PythonAnywhere free accounts require outbound traffic to use their proxy tunnel.
IS_PYTHONANYWHERE = 'PYTHONANYWHERE_SITE' in os.environ
PROXY_URL = 'http://proxy.server:3128'

# I-PASTE MO DITO ANG MAHABANG CLIENT ACCESS TOKEN MULA SA GENIUS
GENIUS_TOKEN = "Lwh7dOi2bTY2TCdAQpe-g5tCOwu3YoTtaPK-e9LWPVCjc8OZf40ro4pIIPb0_Sth"

# Configure lyricsgenius to handle the proxy configuration if deployed live
if IS_PYTHONANYWHERE:
    genius = lyricsgenius.Genius(GENIUS_TOKEN, proxies={'http': PROXY_URL, 'https': PROXY_URL})
else:
    genius = lyricsgenius.Genius(GENIUS_TOKEN)

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
        'lyrics': "⚠️ Lyrics not found in Genius database.\n\nPlease copy and paste the lyrics manually.",
        'youtube_id': ''
    }

    # --- HAKBANG A: KUKUNIN ANG LYRICS (GENIUS) ---
    try:
        song = genius.search_song(title, artist)
        if song and song.lyrics:
            clean_lyrics = song.lyrics.replace(f"{song.title} Lyrics", "", 1).strip()
            if clean_lyrics.endswith("Embed"):
                clean_lyrics = clean_lyrics[:-5].strip()
            clean_lyrics = re.sub(r'\d+$', '', clean_lyrics).strip()
            response_data['lyrics'] = clean_lyrics
    except Exception as e:
        print(f"Genius Error: {e}")

    # --- HAKBANG B: KUKUNIN ANG YOUTUBE VIDEO ID ---
    try:
        if YOUTUBE_API_KEY and YOUTUBE_API_KEY != "I-PASTE_DITO_YUNG_AIzaSy_KEY_MO":
            url = "https://www.googleapis.com/youtube/v3/search"
            search_query = f"{artist} {title} lyrics"
            
            params = {
                'part': 'snippet',
                'q': search_query,
                'type': 'video',
                'videoEmbeddable': 'true',   # Dapat pwedeng i-embed sa code
                'videoSyndicated': 'true',   # 🔥 ETO ANG TUNAY NA SOLUSYON! Dapat pwedeng i-play sa labas ng youtube.com
                'key': YOUTUBE_API_KEY,
                'maxResults': 5
            }
            
            # Conditionally attach proxy configurations for the request library
            proxies = {'http': PROXY_URL, 'https': PROXY_URL} if IS_PYTHONANYWHERE else None
            
            yt_res = requests.get(url, params=params, proxies=proxies, timeout=10).json()
            
            if 'items' in yt_res and len(yt_res['items']) > 0:
                selected_video_id = None
                
                for item in yt_res['items']:
                    channel_title = item['snippet'].get('channelTitle', '')
                    
                    # Siguraduhin pa rin nating i-bypass ang mga Topic channels kung may makalusot
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