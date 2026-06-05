import os
import django

# I-initialize si Django para magamit ang mga models sa labas ng server
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'synco.settings')
django.setup()

from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp
from django.contrib.auth import get_user_model

print("--- SIMULAN ANG AUTOMATED SETUP ---")

# 1. I-configure ang Site ID 1 para sa Render URL
site, created = Site.objects.get_or_create(id=1)
site.domain = 'synco-app.onrender.com'
site.name = 'Synco'
site.save()
print("[OK] Site configured to synco-app.onrender.com")

# 2. GUMAWA NG ADMIN ACCOUNT (SUPERUSER)
# Palitan mo ang 'admin', 'admin@email.com', at 'SyncoAdmin2026!' kung gusto mo
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@email.com', 'SyncoAdmin2026!')
    print("[OK] Superuser 'admin' created successfully!")
else:
    print("[INFO] Superuser 'admin' already exists.")

# 3. I-SETUP ANG GOOGLE SOCIAL APP CREDENTIALS
# Kukunin nito ang susi mula sa Render Environment Variables para ligtas
CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "PLACEHOLDER_CLIENT_ID")
SECRET_KEY = os.environ.get("GOOGLE_SECRET_KEY", "PLACEHOLDER_SECRET_KEY")

app, created = SocialApp.objects.get_or_create(provider='google', name='Google')
app.client_id = CLIENT_ID
app.secret = SECRET_KEY
app.save()
app.sites.add(site)
app.save()
print("[OK] Google SocialApp credentials linked.")

print("--- TAPOS NA ANG SETUP ---")