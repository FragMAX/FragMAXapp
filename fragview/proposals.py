_SESSION_KEY = "proposals"


def set_proposals(request, proposals):
    """
    store list of the proposals accessible to a user in current session
    """
    request.session[_SESSION_KEY] = proposals


def get_proposals(request):
    """
    get the list of the proposals accessible to a user in current session
    """
    return request.session[_SESSION_KEY]
