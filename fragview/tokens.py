from fragview.encryption import generate_token
from fragview.models import AccessToken


def get_valid_token(project):
    """
    get an currently valid access token for specified project,
    or if project does not have one currently, create a new token
    """
    # TODO: take into account 'expiration time' somehow
    toks = AccessToken.objects.filter(project=project)
    if toks.exists():
        return toks.first()

    # no tokens exists, add new
    return AccessToken.add_token(project, generate_token())
