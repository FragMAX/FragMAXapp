from django.shortcuts import redirect
from django import urls
from django.conf import settings
from fragview import projects


def login_required(get_response):
    """
    middleware, that requires login for all URLs except:

    * login URL
    * URL listed in 'OPEN_URLS' setting
    """
    login_url = settings.LOGIN_URL
    open_urls = [login_url] + getattr(settings, "OPEN_URLS", [])

    def check_login(request):
        if not request.user.is_authenticated and \
                request.path_info not in open_urls:
            return redirect(login_url + "?next=" + request.path)

        return get_response(request)

    return check_login


def no_projects_redirect(get_response):
    """
    middleware which in case user does not have access to any projects,
    redirects to 'new project' page
    """
    new_proj_url = urls.reverse("new_project")

    excluded_urls = [
        new_proj_url,
        urls.reverse("logout"),
        urls.reverse("login"),
    ]

    def check_current_project(request):
        if request.path_info not in excluded_urls and \
                projects.current_project(request) is None:
            return redirect(new_proj_url)

        return get_response(request)

    return check_current_project
