import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synco.settings')

# 1. Patakbuhin muna ang default Django application loader
application = get_wsgi_application()

# 2. AUTO-SETUP KUSA PAGKAGISING NG SERVER (Para sa Render Free Tier)
try:
    from django.contrib.sites.models import Site
    from allauth.socialaccount.models import SocialApp

    print("--- EMERGENCE: RUNTIME DATABASE SETUP STARTING ---")

    # Ayusin ang Site ID 1 para sa Render
    site, _ = Site.objects.get_or_create(id=1)
    site.domain = 'synco-app.onrender.com'
    site.name = 'Synco'
    site.save()

    # Kukunin ang sinave mong Environment Variables sa Render Dashboard
    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    secret_key = os.environ.get("GOOGLE_SECRET_KEY")

    if client_id and secret_key:
        app, _ = SocialApp.objects.get_or_create(provider='google', name='Google')
        app.client_id = client_id
        app.secret = secret_key
        app.save()
        app.sites.add(site)
        print("--- [SUCCESS] GOOGLE AUTH CREDENTIALS LINKED TO DATABASE! ---")
    else:
        print("--- [WARNING] GOOGLE KEYS NOT FOUND IN ENVIRONMENT VARIABLES ---")

except Exception as e:
    print(f"--- [ERROR] Runtime setup failed: {e} ---")