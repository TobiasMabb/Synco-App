from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.song_list_view, name='song_list'),
    path('add/', views.song_create_view, name='song_create'),
    path('get-lyrics/', views.get_lyrics_api, name='get_lyrics'),
    path('<int:pk>/', views.song_detail_view, name='song_detail'),
    path('<int:pk>/delete/', views.song_delete_view, name='song_delete'),
    path('api/fetch-chords/', views.fetch_chords_api, name='api_fetch_chords'),
    path('songs/api/transpose/', views.transpose_api, name='transpose_api'),
    path('password_change/', auth_views.PasswordChangeView.as_view(success_url='/songs/'), name='password_change'),
]