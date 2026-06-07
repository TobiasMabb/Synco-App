# synco/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

# Views
from songs.views import song_list_view
from .views import login_view, dashboard_view

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    # ---------------------------------------------------------
    # MAIN PAGE: Nakaturo na ngayon sa song_list_view
    # ---------------------------------------------------------
    path('', song_list_view, name='home'), 

    # Auth / Accounts
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),

    # App URLs
    path('dashboard/', include('core.urls')),
    path('songs/', include('songs.urls')),
    path('setlists/', include('setlists.urls')),

    # PWA (Progressive Web App) Files
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript'
    )),
    path('manifest.json', TemplateView.as_view(
        template_name='manifest.json',
        content_type='application/json'
    )),
]