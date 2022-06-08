from django.shortcuts import redirect
from django import urls
from django.conf import settings
from fragview import projects
from fragview.proposals import get_proposals


def _open_urls():
    return [settings.LOGIN_URL] + settings.OPEN_URLS


def login_required(get_response):
    """
    middleware, that requires login for all URLs except:

    * login URL
    * URL listed in 'OPEN_URLS' setting
    """
    login_url = settings.LOGIN_URL

    def check_login(request):
        if not request.user.is_authenticated and \
                request.path_info not in _open_urls() and \
                not request.path_info.startswith("/hack/proj_details"):
            return redirect(login_url + "?next=" + request.path)

        return get_response(request)

    return check_login


def no_projects_redirect(get_response):
    """
    middleware which in case user does not have access to any projects,
    redirects to the 'new project' page or 'manage project' in case
    he/she have some pending project in flight
    """
    new_proj_url = urls.reverse("new_project")
    manage_projects_url = urls.reverse("manage_projects")

    excluded_urls = [
        new_proj_url,
        manage_projects_url,
        urls.reverse("logout"),
        urls.reverse("commit"),
    ] + _open_urls()

    def _get_redirect_url(request):
        if projects.have_pending_projects(request):
            return manage_projects_url
        return new_proj_url

    def _is_excluded_url(url):
        if url in excluded_urls:
            return True

        # allows to browse fragment libraries before creating a project
        if url.startswith("/libraries") or url.startswith("/fragment"):
            return True

        # allows to delete failed projects, in cases
        # when user have only one pending project,
        # that have failed during set-up
        if url.startswith("/project/"):
            return True

        if url.startswith("/hack/proj_details"):
            return True

        return False

    def check_current_project(request):
        if _is_excluded_url(request.path_info):
            return get_response(request)

        proposals = get_proposals(request)
        current_project = request.user.get_current_project(proposals)
        if current_project is None:
            return redirect(_get_redirect_url(request))

        return get_response(request)

    return check_current_project


def key_required_redirect(get_response):
    """
    middleware that check if currently selected is in encrypted mode
    and does not have it's encryption key uploaded, in that case
    redirect user to key upload page
    """
    def _is_excluded_url(url):
        excluded_prefixes = [
            "/encryption/",          # avoid redirection loop
            settings.LOGIN_URL,      # no user thus no current project
            "/libraries",            # makes possible to browse libraries without existing project
            "/fragment",
            urls.reverse("logout"),  # no current project when logging out
            urls.reverse("commit"),
            "/project",              # exclude all project management URLs
            "/crypt/",               # crypt I/O use tokens rather then user authentication
            "/hack/proj_details"
        ]

        for excluded_prefix in excluded_prefixes:
            if url.startswith(excluded_prefix):
                return True

        return False

    def _key_needed(request):
        proposals = get_proposals(request)
        project = request.user.get_current_project(proposals)

        if not project.encrypted:
            return False

        return not project.has_encryption_key()

    def check_encryption_key(request):
        if _is_excluded_url(request.path_info) or not _key_needed(request):
            return get_response(request)

        return redirect(urls.reverse("encryption"))

    return check_encryption_key
