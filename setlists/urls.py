# setlists/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.setlist_list_view, name='setlist_list'),
    path('new/', views.setlist_create_view, name='setlist_create'),
    path('<int:pk>/', views.setlist_detail_view, name='setlist_detail'),
    path('<int:pk>/add-song/', views.add_song_to_setlist, name='add_song_to_setlist'),
    path('<int:pk>/remove-song/<int:song_id>/', views.remove_song_from_setlist, name='remove_song_from_setlist'),
    path('<int:pk>/print/', views.setlist_print_view, name='setlist_print'),
]