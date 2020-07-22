import re
from fragview.sites import SITE
from fragview.models import Project
from .proposals import get_proposals


def site(request):
    """
    Adds site specific parameters to template context.
    """
    disabled_features = {
        feature: True for feature in SITE.DISABLED_FEATURES
    }

    ctx = {
        # site logo image
        "site_logo": SITE.LOGO,
        # features disabled for this site
        "disabled": disabled_features,
    }

    if not request.user.is_authenticated:
        # user not logged in, add login view specific parameter
        ctx["account_style"] = SITE.ACCOUNT_STYLE

    return ctx


def projects(request):
    """
    Adds a projects related data to template context.
    """
    if not request.user.is_authenticated:
        # user not logged in, no projects context
        return {}

    proposals = get_proposals(request)

    return {
        # list of all projects that are accessable to the user
        "projects": Project.user_projects(proposals),
        # user's currently selected project
        "project": request.user.get_current_project(proposals),
    }


class ActiveMenuCtx:
    """
    Using the regular expression we check if the request URLs have an active menu.

    Each group of URLs with same active menu are expressed as named regexp group.
    If URL matches some group, we add that group's name as 'active_menu' template context variable.
    """

    URL_REGEXP = (
        r"(?P<project>^/pdb/add|^/pdb/\d*|^/pdbs|^/project_details|^/library_view|^/encryption|^/$)|"
        + r"(?P<pandda>^/pandda_analyse/$|^/pandda_inspect/$|^/pandda_export/$)"
    )
    # URLs 'project' submenus

    def __init__(self):
        self.url_regexp = re.compile(self.URL_REGEXP)

    def __call__(self, request):
        match = self.url_regexp.match(request.path_info)
        if match is None:
            return {}

        return {"active_menu": match.lastgroup}


active_menu = ActiveMenuCtx()
