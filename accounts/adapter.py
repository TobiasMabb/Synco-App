from django.core.exceptions import MultipleObjectsReturned
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    def get_app(self, request, provider, client_id=None):
        try:
            return super().get_app(request, provider, client_id)
        except MultipleObjectsReturned:
            apps = self.list_apps(request, provider=provider, client_id=client_id)
            visible_apps = [app for app in apps if not app.settings.get("hidden")]
            if visible_apps:
                return visible_apps[0]
            return apps[0]
