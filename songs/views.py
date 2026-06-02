import os
import re
import requests
import lyricsgenius
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .models import Song

# I-PASTE MO DITO ANG MAHABANG CLIENT ACCESS TOKEN MULA SA GENIUS
GENIUS_TOKEN = "Lwh7dOi2bTY2TCdAQpe-g5tCOwu3YoTtaPK-e9LWPVCjc8OZf40ro4pIIPb0_Sth"
genius = lyricsgenius.Genius(GENIUS_TOKEN)

# Itatago nito ang mga technical logs sa terminal para malinis tignan
genius.verbose = False 

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def song_list_view(request):
    songs = Song.objects.all().order_by('-created_at')
    return render(request, 'songs/song_list.html', {'songs': songs})

def song_create_view(request):
    if request.method == "POST":
        title = request.POST.get('title')
        artist = request.POST.get('artist')
        lyrics = request.POST.get('lyrics', '')
        chords = request.POST.get('chords', '')
        
        # YouTube API Fetch
        url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={title}+{artist}&type=video&key={YOUTUBE_API_KEY}&maxResults=1"
        yt_id = None
        try:
            yt_id = requests.get(url).json()['items'][0]['id']['videoId']
        except: 
            pass
        
        Song.objects.create(title=title, artist=artist, lyrics=lyrics, chords=chords, youtube_id=yt_id)
        return redirect('song_list')
    return render(request, 'songs/add_song.html')

def get_lyrics_api(request):
    title = request.GET.get('title', '').strip()
    artist = request.GET.get('artist', '').strip()
    
    if not title or not artist:
        return JsonResponse({'lyrics': 'Please enter both Title and Artist.'})

    try:
        # Hahanapin ang kanta gamit ang Genius Library
        song = genius.search_song(title, artist)
        
        if song and song.lyrics:
            # Paglilinis sa lyrics output ng Genius
            clean_lyrics = song.lyrics.replace(f"{song.title} Lyrics", "", 1).strip()
            
            # Tinatanggal ang "Embed" at mga random numbers sa dulo ng text
            if clean_lyrics.endswith("Embed"):
                clean_lyrics = clean_lyrics[:-5].strip()
            clean_lyrics = re.sub(r'\d+$', '', clean_lyrics).strip()
            
            return JsonResponse({'lyrics': clean_lyrics})
            
    except Exception as e:
        print(f"Genius Error: {e}")
        pass
        
    return JsonResponse({
        'lyrics': "⚠️ Lyrics not found in Genius database.\n\nPlease copy and paste the lyrics manually."
    })

def song_detail_view(request, pk):
    return render(request, 'songs/song_detail.html', {'song': get_object_or_404(Song, pk=pk)})

def song_delete_view(request, pk):
    get_object_or_404(Song, pk=pk).delete()
    return redirect('song_list')