from django.db import models
from django.conf import settings # 👈 1. Idagdag itong import na 'to

class Song(models.Model):
    # 🚨 2. Idagdag itong ForeignKey field sa unahan
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='songs'
    )
    title = models.CharField(max_length=200)
    artist = models.CharField(max_length=200)
    lyrics = models.TextField()
    chords = models.TextField()
    youtube_id = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # Optional pero maganda para hindi "Song object (30)" ang makita mo sa admin panel
    def __str__(self):
        return f"{self.title} - {self.artist}"