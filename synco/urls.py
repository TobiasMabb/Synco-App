from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

from songs.views import song_list_view

urlpatterns = [
    path('admin/', admin.site.urls),

    # HOME PAGE
    path('', song_list_view, name='home'),

    # APPS
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),

    path('dashboard/', include('core.urls')),
    path('songs/', include('songs.urls')),
    path('setlists/', include('setlists.urls')),
    path('settings/', include('settings_page.urls')),

    # PWA FILES
    path('sw.js', TemplateView.as_view(
        template_name='sw.js',
        content_type='application/javascript'
    )),

    path('manifest.json', TemplateView.as_view(
        template_name='manifest.json',
        content_type='application/json'
    )),
]