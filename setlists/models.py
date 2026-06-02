from django.db import models
from django.contrib.auth.models import User
from songs.models import Song

class Setlist(models.Model):
    title = models.CharField(max_length=200)
    event_date = models.DateField()
    notes = models.TextField(blank=True, help_text="e.g., Soundcheck at 4 PM, special reminders")
    songs = models.ManyToManyField(Song, through='SetlistSong', related_name='setlists')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.event_date.strftime('%b %d, %Y')}"

class SetlistSong(models.Model):
    setlist = models.ForeignKey(Setlist, on_delete=models.CASCADE)
    song = models.ForeignKey(Song, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, help_text="Performance order of the song")

    class Meta:
        ordering = ['order']
        unique_together = ('setlist', 'song')

    def __str__(self):
        return f"{self.setlist.title} -> {self.song.title} (#{self.order})"