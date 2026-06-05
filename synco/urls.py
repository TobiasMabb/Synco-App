from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from .views import login_view

urlpatterns = [
    path('admin/', admin.site.urls),

    path('', login_view, name='home'),

    # keep ONLY ONE accounts routing
    path('accounts/', include('allauth.urls')),

    path('dashboard/', include('core.urls')),
    path('songs/', include('songs.urls')),
    path('setlists/', include('setlists.urls')),

    path(
        'sw.js',
        TemplateView.as_view(template_name='sw.js', content_type='application/javascript')
    ),
    path(
        'manifest.json',
        TemplateView.as_view(template_name='manifest.json', content_type='application/json')
    ),
]