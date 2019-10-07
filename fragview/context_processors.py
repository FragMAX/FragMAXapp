from fragview.models import Project


def projects(request):
    """
    Adds a 'projects' entry to template context, which is
    a list of the projects a user have access to.
    """
    if not request.user.is_authenticated:
        # user not logged in, no projects context
        return {}

    return {"projects": Project.user_projects()}
