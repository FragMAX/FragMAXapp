from fragview.projects import Project
from fragview.models import AccessToken


def get_valid_token(project: Project):
    """
    get an currently valid access token for specified project,
    or if project does not have one currently, create a new token
    """
    token = AccessToken.get_project_token(project.id)
    if token is not None:
        return token

    return AccessToken.create_new(project.id)
