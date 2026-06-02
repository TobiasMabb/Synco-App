# setlists/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Setlist, SetlistSong
from .forms import SetlistForm
from songs.models import Song

@login_required
def setlist_list_view(request):
    setlists = Setlist.objects.filter(created_by=request.user).order_by('-event_date')
    return render(request, 'setlists/setlist_list.html', {'setlists': setlists})

@login_required
def setlist_detail_view(request, pk):
    setlist = get_object_or_404(Setlist, pk=pk)
    # Fetch songs currently in this setlist, ordered
    current_set_songs = SetlistSong.objects.filter(setlist=setlist).order_by('order')
    
    # Exclude songs already in the setlist so we can display options to add new ones
    already_added_ids = current_set_songs.values_list('song_id', flat=True)
    available_songs = Song.objects.exclude(id__in=already_added_ids).order_by('title')

    return render(request, 'setlists/setlist_detail.html', {
        'setlist': setlist,
        'current_set_songs': current_set_songs,
        'available_songs': available_songs,
    })

@login_required
def setlist_create_view(request):
    if request.method == 'POST':
        form = SetlistForm(request.POST)
        if form.is_valid():
            setlist = form.save(commit=False)
            setlist.created_by = request.user
            setlist.save()
            messages.success(request, f'Setlist "{setlist.title}" created successfully!')
            return redirect('setlist_detail', pk=setlist.pk)
    else:
        form = SetlistForm()
    return render(request, 'setlists/setlist_form.html', {'form': form})

@login_required
def add_song_to_setlist(request, pk):
    setlist = get_object_or_404(Setlist, pk=pk)
    if request.method == 'POST':
        song_id = request.POST.get('song_id')
        if song_id:
            song = get_object_or_404(Song, id=song_id)
            # Find the next order index
            next_order = SetlistSong.objects.filter(setlist=setlist).count() + 1
            SetlistSong.objects.get_or_create(setlist=setlist, song=song, defaults={'order': next_order})
            messages.success(request, f'Added "{song.title}" to the setlist.')
    return redirect('setlist_detail', pk=setlist.pk)

@login_required
def remove_song_from_setlist(request, pk, song_id):
    setlist = get_object_or_404(Setlist, pk=pk)
    setlist_song = get_object_or_404(SetlistSong, setlist=setlist, song_id=song_id)
    setlist_song.delete()
    messages.info(request, "Song removed from setlist.")
    
    # Re-index remaining items to close any order gaps
    remaining = SetlistSong.objects.filter(setlist=setlist).order_by('order')
    for index, item in enumerate(remaining, start=1):
        item.order = index
        item.save()
        
    return redirect('setlist_detail', pk=setlist.pk)

@login_required
def setlist_print_view(request, pk):
    setlist = get_object_or_404(Setlist, pk=pk)
    current_set_songs = SetlistSong.objects.filter(setlist=setlist).order_by('order')
    
    # Build a plain text string representation for easy chat copy-pasting
    text_lines = [
        f"=== SETLIST: {setlist.title} ===",
        f"Date: {setlist.event_date.strftime('%A, %b %d, %Y')}",
        "==============================",
        ""
    ]
    for item in current_set_songs:
        text_lines.append(f"{item.order}. {item.song.title} [Key: {item.song.key}] - {item.song.artist}")
        
    if setlist.notes:
        text_lines.extend(["", "--- Notes ---", setlist.notes])
        
    plain_text = "\n".join(text_lines)

    return render(request, 'setlists/setlist_print.html', {
        'setlist': setlist,
        'current_set_songs': current_set_songs,
        'plain_text': plain_text,
    })