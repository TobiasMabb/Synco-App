# 🎵 SYNCO - Music Chords & Lyrics App

**SYNCO** is a robust, production-ready Django web application designed for musicians, worship leaders, and bands. It serves as a centralized smart hub to manage song libraries, organize setlists, fetch lyrics or chords dynamically via a multi-engine fallback scraper, and transpose song sheets on the fly without page reloads.

---

## ✨ Features

### 🔒 Core & Authentication
* **Secure Routing Gateway:** Full site protection using Django's native `@login_required` decorators across the dashboard, song database, and API endpoints. Unauthenticated users are automatically rerouted to the secure gateway.
* **Authentication Suite:** Pre-configured with `django-allauth` to handle robust user signup, secure login/logout flows, and seamless future social auth integration (e.g., Google OAuth).

### 🎼 Smart Chords & Transposition Engine
* **Anti-Block Chord Scraper:** A advanced scraper that utilizes Strategy-Based Fallbacks (Direct URL Guessing ➡️ DuckDuckGo HTML/Lite Gateways ➡️ Chordie Internal Search) to bypass standard anti-scraping blocks.
* **Ultimate Guitar JSON Bypass:** Equipped with a sealed parser that extracts raw chord contents directly from Ultimate Guitar’s encrypted inline client-state data store (`.js-store`).
* **Live Transposition Engine:** An AJAX-powered backend utility that handles real-time transposition over the 12-semitone chromatic scale wheel. It accurately shifts complex tokens, suffixes (e.g., `maj7`, `sus4`, `dim`), and slash chords (e.g., `D/F#` to `E/G#`).
* **Chord Formatting Sanitizer:** Automatically processes chaotic raw text inputs, converts tabs to aligned spaces, strips redundant trailing whitespaces, and enforces a strict 1-blank-line maximum for beautiful monospace sheet display.

### 📝 Lyrics & Media Automation
* **3-Engine Lyrics Fallback:** Seamlessly requests lyrics across multiple free endpoints: **LRCLIB (Fuzzy Search)** ➡️ **LRCLIB (Exact Get)** ➡️ **Lyrics.ovh API**.
* **Timestamp Stripper:** Built-in regex filters that automatically clean synced lyric files (`[00:00.00]`) into readable, plain text sheets.
* **YouTube Automation Wrapper:** Automatically pulls official media audio IDs via the YouTube Data API v3, with an embedded scrap-fallback handler through anonymous search engines when API quotas are exceeded.

### 📱 PWA Ready
* Configured with application service workers (`sw.js`) and structural manifests (`manifest.json`) for progressive web app compliance and future offline viewing capabilities.

---

## 🛠️ Tech Stack

* **Backend Framework:** Django (Python)
* **Web Scraping & Parsing:** BeautifulSoup4, Requests, Python Regex (`re`)
* **Frontend Interaction:** JavaScript (Asynchronous AJAX Engine), HTML5 (Monospace Renderers), CSS3
* **Authentication Core:** django-allauth

---

## 🔌 API Integrations

| Provider | Endpoint Purpose | Fallback Priority |
| :--- | :--- | :--- |
| **LRCLIB API** | Plain & Synced Track Lyrics Search | Primary / Secondary |
| **Lyrics.ovh** | Text-based lyric extraction matching | Tertiary Resort |
| **YouTube v3 API** | Automated video ID attachment | Primary Video |
| **DuckDuckGo HTML/Lite** | IP-Block avoidance & Scrape Gateway | Automated Fallback |

---

## 📁 Project Architecture

```text
synco_project/
│
├── synco/                      # Global Project Configuration Core
│   ├── settings.py             # App configurations, allauth keys, auth validators
│   ├── urls.py                 # Core URL router mapping authentication and app routes
│   └── views.py                # Main system routing logic (Dashboard views)
│
├── songs/                      # Core Inventory App
│   ├── models.py               # Song schema structures (chords, lyrics, youtube metadata)
│   ├── views.py                # CRUD controllers, transposition utilities, and scrapers
│   └── urls.py                 # Route mappings for the lyrics and chord engines
│
├── setlists/                   # Setlist Management App
│   └── models.py               # User-curated event playlist flow structures
│
├── core/                       # Core Layout/Dashboard App
└── templates/                  # Base structural frontend layout components

🚀 Installation & Local Setup
1. Clone and Navigate to the Project
Bash
git clone <your-repository-url>
cd synco_project

2. Set Up a Virtual Environment
Bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate




3. Install Required Dependencies
Bash
pip install -r requirements.txt




4. Environment Configurations
Create a .env file in the project root folder to configure third-party services:

Code snippet
DEBUG=True
SECRET_KEY=your_django_secret_key_here
YOUTUBE_API_KEY=your_optional_youtube_data_api_v3_key



5. Execute Database Migrations
Bash
python manage.py migrate


6. Create an Administrative Superuser
Bash
python manage.py createsuperuser



7. Fire Up the Development Server
Bash
python manage.py runserver
Go to http://127.0.0.1:8000/ in your browser. Unauthenticated traffic will instantly be redirected to the accounts login portal!