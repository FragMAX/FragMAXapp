"""
Django authentication backend for local users database.

Implements username and password authentication against the local database This backend uses the
'User' model to check credentials.

This is intended for sites where integrating with another authentication system is not desirable.
"""
from fragview.auth.utils import AuthBackend
from fragview.models import User
from fragview.proposals import set_proposals


class LocalBackend(AuthBackend):
    def authenticate(self, request, username, password):
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return

        if not user.check_password(password):
            # wrong password
            return

        #
        # this is a HZB specific hack for now, as local auth is only used at that site right now
        #
        # HZB uses username as path to the data folder instead of proposal number and shift
        #
        set_proposals(request, [username])

        return user
