"""
Django middleware, that requires login for all URLs except:

* login URL
* URL listed in 'OPEN_URLS' setting
"""
from django.shortcuts import redirect
from django.conf import settings


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.login_url = settings.LOGIN_URL
        self.open_urls = [self.login_url] + getattr(settings, "OPEN_URLS", [])

    def __call__(self, request):
        if not request.user.is_authenticated and \
                request.path_info not in self.open_urls:
            return redirect(self.login_url + "?next=" + request.path)

        return self.get_response(request)
