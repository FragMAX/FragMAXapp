from unittest.mock import Mock
from django import test
from fragview.models import User
from fragview import auth


class TestAuth(test.TestCase):
    """
    test local DB authentication backend
    """

    USER_NAME = "kiwi"
    PASSWORD = "peak"

    def setUp(self):
        self.backend = auth.LocalBackend()

        user = User(username=self.USER_NAME)
        user.set_password(self.PASSWORD)
        user.save()

        self.request = Mock()
        self.request.session = dict()

    def test_valid(self):
        """
        test successfull authentication
        """
        user = self.backend.authenticate(self.request, self.USER_NAME, self.PASSWORD)
        self.assertEqual(user.username, self.USER_NAME)

        # check that session have correct 'list' of proposals set
        self.assertDictEqual(self.request.session, dict(proposals=[self.USER_NAME]))

    def test_unknown_user(self):
        """
        case when no user with specified username exist
        """
        res = self.backend.authenticate(self.request, "vlatal", "")
        self.assertIsNone(res)

    def test_wrong_password(self):
        """
        case when user name is correct, but the password is wrong
        """
        res = self.backend.authenticate(self.request, self.USER_NAME, "hello")
        self.assertIsNone(res)
