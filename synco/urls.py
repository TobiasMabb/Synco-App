from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from .views import dashboard_view, login_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('pwa.urls')),
    path('', login_view, name='home'),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', include('core.urls')),
    path('songs/', include('songs.urls')),
    path('setlists/', include('setlists.urls')),
    path('sw.js', TemplateView.as_view(template_name='sw.js', content_type='application/javascript'), name='sw_js'),
    path('manifest.json', TemplateView.as_view(template_name='manifest.json', content_type='application/json'), name='manifest_json'),
]