import unittest
from unittest.mock import patch, Mock
from json.decoder import JSONDecodeError
from django import test
from django.conf import settings
from django.contrib.auth.models import User
from fragview import auth

ISPYB_ERR_MSG = \
    "JBAS011843: Failed instantiate InitialContextFactory com.sun.jndi.ldap.LdapCtxFactory " \
    "from classloader ModuleClassLoader for Module \"deployment.ispyb.ear.ispyb-ws.war:main\" " \
    "from Service Module Loader"

USER = "user1"
PASS = "pass1"
TOKEN = "token1234"


class TestExpectedErrMsgFunc(unittest.TestCase):
    """
    test auth._expected_ispyb_err_msg()
    """
    def test_unexpected_message(self):
        self.assertFalse(auth._expected_ispyb_err_msg("oranges and apples"))

    def test_expected_message(self):
        self.assertTrue(auth._expected_ispyb_err_msg(ISPYB_ERR_MSG))


class TestCheckIspybErrorMessageFunc(unittest.TestCase):
    """
    test auth._check_ispyb_error_message()
    """
    @patch("logging.warning")
    def test_unexpected_message(self, log_wrn_mock):
        response = Mock()
        response.status_code = 200
        response.reason = "OK"
        response.text = "orange"

        auth._check_ispyb_error_message(response)
        log_wrn_mock.assert_called_once_with(
            "unexpected response from ISPyB\n200 OK\norange")

    @patch("logging.warning")
    def test_expected_message(self, log_wrn_mock):
        response = Mock()
        response.text = ISPYB_ERR_MSG

        auth._check_ispyb_error_message(response)
        log_wrn_mock.assert_not_called()


class TestIspubAuthenticateFunc(unittest.TestCase):
    """
    test auth._ispyb_authenticate()
    """

    HOST = "example.com"
    SITE = "TstSite"

    def test_good_creds(self):
        response = Mock()
        response.json.return_value = dict(token=TOKEN)

        with patch("requests.post", Mock(return_value=response)) as post:
            token = auth._ispyb_authenticate(self.HOST, self.SITE, USER, PASS)
            self.assertEqual(token, TOKEN)

            post.assert_called_once_with(
                "https://example.com/ispyb/ispyb-ws/rest/authenticate?site=TstSite",
                data={"login": "user1", "password": "pass1"},
                headers={"content-type": "application/x-www-form-urlencoded"})

    def test_invalid_creds(self):
        response = Mock()
        response.text = ISPYB_ERR_MSG
        response.json.side_effect = JSONDecodeError("", "", 0)

        with patch("requests.post", Mock(return_value=response)) as post:
            token = auth._ispyb_authenticate(self.HOST, self.SITE, USER, PASS)
            self.assertIsNone(token)

            post.assert_called_once_with(
                "https://example.com/ispyb/ispyb-ws/rest/authenticate?site=TstSite",
                data={"login": "user1", "password": "pass1"},
                headers={"content-type": "application/x-www-form-urlencoded"})


class TestISPyBBackendInvalidCreds(unittest.TestCase):
    def test_invalid_creds(self):
        backend = auth.ISPyBBackend()

        auth_mock = Mock(return_value=None)
        with patch("fragview.auth._ispyb_authenticate", auth_mock):
            user_obj = backend.authenticate(None, "usrn", "passd")
            self.assertIsNone(user_obj)

        auth_mock.assert_called_once_with(
            settings.ISPYB_AUTH_HOST, settings.ISPYB_AUTH_SITE,
            "usrn", "passd")


class TestISPyBBackendAuthenticate(test.TestCase):
    """
    test ISPyBBackend.authenticate() method
    """
    def setUp(self):
        self.backend = auth.ISPyBBackend()
        self.auth_mock = Mock(return_value=TOKEN)

    def test_first_time_valid(self):

        # check that user does not exist in the database
        self.assertFalse(User.objects.filter(username=USER).exists())

        with patch("fragview.auth._ispyb_authenticate", self.auth_mock):
            user_obj = self.backend.authenticate(None, USER, PASS)

            # smoke tests created user object
            self.assertEqual(user_obj.username, USER)

            # check that user have been added to the database
            self.assertTrue(User.objects.filter(username=USER).exists())

    def test_existing_user_login(self):
        # add test user to the database
        User(username=USER).save()

        with patch("fragview.auth._ispyb_authenticate", self.auth_mock):
            user_obj = self.backend.authenticate(None, USER, PASS)

            # smoke tests returned user object
            self.assertEqual(user_obj.username, USER)

            # the user still should be in the database
            self.assertTrue(User.objects.filter(username=USER).exists())


class TestISPyBBackendGetUser(test.TestCase):
    """
    test ISPyBBackend.get_user()
    """
    def test_user_exists(self):
        # add test user to the database
        user = User(username=USER)
        user.save()

        res = auth.ISPyBBackend().get_user(user.id)
        self.assertEqual(user.id, res.id)

    def test_user_does_not_exists(self):
        NONEXIST_ID = -1

        self.assertFalse(User.objects.filter(id=NONEXIST_ID))
        res = auth.ISPyBBackend().get_user(NONEXIST_ID)
        self.assertIsNone(res)
