# synco/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from songs.models import Song
from setlists.models import Setlist

def login_view(request):
    return render(request, 'accounts/login.html')

@login_required
def dashboard_view(request):
    total_songs = Song.objects.count()
    total_setlists = Setlist.objects.filter(created_by=request.user).count()
    recent_setlists = Setlist.objects.filter(created_by=request.user).order_by('-event_date')[:3]
    
    context = {
        'total_songs': total_songs,
        'total_setlists': total_setlists,
        'recent_setlists': recent_setlists,
    }
    
    return render(request, 'core/dashboard.html', context)