echo "# SYNCO - Music Chords & Lyrics App

## Overview
SYNCO is a Django-based web application that automatically fetches song lyrics, guitar chords, and YouTube video links. It also supports chord formatting, transposition, and live AJAX-based updates.

## Features
- Auto lyrics fetching (LRCLIB + Lyrics.ovh fallback)
- Auto chord scraping (E-Chords, Tabs4Acoustic, Chordie)
- YouTube video auto-search
- Live chord transposition (E → G, etc.)
- Clean chord formatting engine
- AJAX-powered frontend APIs

## Tech Stack
- Django
- Python Requests
- BeautifulSoup
- JavaScript (AJAX)
- HTML/CSS

## APIs Used
- https://lrclib.net
- https://api.lyrics.ovh
- YouTube Data API (optional)
- DuckDuckGo scraping fallback

## How to Run
```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver