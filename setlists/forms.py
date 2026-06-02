# setlists/forms.py
from django import forms
from .models import Setlist

class SetlistForm(forms.ModelForm):
    class Meta:
        model = Setlist
        fields = ['title', 'event_date', 'notes']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-zinc-700',
                'placeholder': 'e.g., Sunday Morning Worship, Youth Night'
            }),
            'event_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-zinc-700'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'w-full bg-zinc-950 border border-zinc-800 rounded-xl p-3 text-white focus:outline-none focus:border-zinc-700',
                'placeholder': 'Add flow details, soundcheck times, or key reminders...'
            }),
        }