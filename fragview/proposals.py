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
    # TO DO find where it needs to be added as a list in the project.
    # This is just a workaround for now
    if not type(request.session[_SESSION_KEY]) == list:
        return [request.session[_SESSION_KEY]]
    return request.session[_SESSION_KEY]