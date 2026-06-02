from django import forms
from .models import Song

class SongForm(forms.ModelForm):
    class Meta:
        model = Song
        fields = ['title', 'artist', 'key', 'bpm', 'youtube_link', 'lyrics']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brandBlue focus:border-transparent transition'}),
            'artist': forms.TextInput(attrs={'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brandBlue focus:border-transparent transition'}),
            'key': forms.TextInput(attrs={'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brandBlue focus:border-transparent transition', 'placeholder': 'e.g., G, C#, F#m'}),
            'bpm': forms.NumberInput(attrs={'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brandBlue focus:border-transparent transition'}),
            'youtube_link': forms.URLInput(attrs={'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brandBlue focus:border-transparent transition'}),
            'lyrics': forms.Textarea(attrs={'rows': 12, 'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl px-4 py-3 text-sm text-white focus:outline-none focus:ring-2 focus:ring-brandBlue focus:border-transparent transition font-mono', 'placeholder': '[C] Amazing Grace\n[F] How sweet the sound...'}),
        }