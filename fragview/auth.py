"""
Django authentication backend for ISPyB.

Implements username and password authentication against the ISPyB using it's RESP API.

This backend expects following django setting variables to exists:

ISPYB_AUTH_HOST = "<ISPub-host>"
ISPYB_AUTH_SITE = "<auth-site>"

Where:
  ISPYB_AUTH_HOST is the fully qualified host name where ISPyB system can be reached.
  ISPYB_AUTH_SITE the site name to use in the authentication queries, e.g. 'MAXIV'
"""

import logging
import requests
from json.decoder import JSONDecodeError
from django.conf import settings
from fragview.models import User
from .proposals import set_proposals


def _expected_ispyb_err_msg(error_msg):
    import re
    match = re.match("^JBAS011843: Failed instantiate.*ldap.*ispyb", error_msg)
    return match is not None


def _check_ispyb_error_message(response):
    #
    # check that we got the 'expected' error message on invalid credentials,
    # otherwise log the error message, so we don't swallow new error messages
    #
    if _expected_ispyb_err_msg(response.text):
        # all is fine
        return

    logging.warning(
        f"unexpected response from ISPyB\n" +
        f"{response.status_code} {response.reason}\n{response.text}")


def _ispyb_authenticate(auth_host, site, user, password):
    url = f"https://{auth_host}/ispyb/ispyb-ws/rest/authenticate?site={site}"

    response = requests.post(
        url,
        headers={'content-type': 'application/x-www-form-urlencoded'},
        data={'login': user, 'password': password})

    try:
        jsn = response.json()
    except JSONDecodeError:
        # on invalid credentials, some ISPyB systems will reply with
        # an internal error message, as plain text
        _check_ispyb_error_message(response)
        return

    return jsn["token"]


def _get_mx_proposals(proposals):
    """
    filter out MX proposals numbers from ISPyB's reply
    """
    props = []
    for prop in proposals:
        if prop["Proposal_proposalCode"] != "MX":
            # skip all non MX (other beamlines) proposals
            continue

        props.append(prop["Proposal_proposalNumber"])

    return props


def _ispyb_get_proposals(auth_host, token):
    url = f"https://{auth_host}/ispyb/ispyb-ws/rest/{token}/proposal/list"
    response = requests.get(url)

    #
    # if can't get proposals list from ISPyB, then we don't
    # know which projects are accessible to the user
    #
    # our app is then effectively broken as well, thrown en error,
    # and hope the getting proposals list can get sorted out ASAP
    #
    if response.status_code != 200:
        raise Exception("could not fetch proposals list\n" +
                        f"got '{response.status_code} {response.reason}' response")

    try:
        props_data = response.json()
    except JSONDecodeError:
        raise Exception("could not parse proposals data, invalid json reply")

    return _get_mx_proposals(props_data)


class ISPyBBackend:
    """
    Check the username and password agains ISPByP system.
    On first successfully login, creates an entry for the account in the local
    users database.

    Each time we login, fetch user's proposals list and store it in the current session.
    """
    def _get_user_obj(self, username):
        user = User.objects.filter(username=username)
        if user.exists():
            return user.first()

        # first time login, create new entry in the database
        user = User(username=username)
        user.save()

        return user

    def authenticate(self, request, username, password):
        token = _ispyb_authenticate(
            settings.ISPYB_AUTH_HOST,
            settings.ISPYB_AUTH_SITE,
            username, password)

        if token is None:
            # autenticaton failed
            return None

        # get user's proposals from ISPyB
        proposals = _ispyb_get_proposals(settings.ISPYB_AUTH_HOST, token)

        # store the proposals list in current session, to be used
        # for granting access to the projects
        set_proposals(request, proposals)

        return self._get_user_obj(username)

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
