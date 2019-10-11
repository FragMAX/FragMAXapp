from fragview.models import Project
from .proposals import get_proposals


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
