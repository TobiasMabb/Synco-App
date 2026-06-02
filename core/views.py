# core/views.py
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from songs.models import Song
from setlists.models import Setlist

@login_required
def dashboard_view(request):
    # Fetch real counts from the database
    total_songs = Song.objects.count()
    total_setlists = Setlist.objects.filter(created_by=request.user).count()
    
    # Calculate upcoming live dates (today or in the future)
    today = timezone.now().date()
    upcoming_schedules = Setlist.objects.filter(
        created_by=request.user, 
        event_date__gte=today
    ).count()
    
    # Grab the latest entries for the activity logs
    recent_songs = Song.objects.order_by('-created_at')[:3]
    recent_setlists = Setlist.objects.filter(created_by=request.user).order_by('-event_date')[:3]

    context = {
        'total_songs': total_songs,
        'total_setlists': total_setlists,
        'upcoming_schedules': upcoming_schedules,
        'recent_songs': recent_songs,
        'recent_setlists': recent_setlists,
    }
    return render(request, 'core/dashboard.html', context)