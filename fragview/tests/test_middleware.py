import unittest
from django import urls
from unittest import mock
from fragview import middleware


class MiddlewareTestsMixin:
    """
    utility class for testing our middleware implementations
    """
    def setUp(self):
        self.get_resp_mock = mock.Mock()
        self.middleware_callable = self.MIDDLEWARE(self.get_resp_mock)

    def _assert_no_redirect(self, result):
        # check that middleware returned 'process request as usual' result
        self.assertEqual(result, self.get_resp_mock.return_value)

    def _assert_redirect(self, result, redirect_url):
        self.assertEqual(result.status_code, 302)
        self.assertEqual(result.url, redirect_url)

    def _request_mock(self, path="/", authenticated=True, with_project=False):
        req = mock.Mock()
        req.path = path  # in our case, path and path_info are the same
        req.path_info = path

        req.session = dict(proposals=["12344321"])

        req.user.is_authenticated = authenticated

        if not with_project:
            req.user.get_current_project.return_value = None

        return req


class TestLoginRequired(MiddlewareTestsMixin, unittest.TestCase):
    """
    test login_required() middleware
    """

    # use 'staticmethod' to create unbound function call to middleware factory function,
    # otherwise 'MIDDLEWARE' becomes a class method
    MIDDLEWARE = staticmethod(middleware.login_required)

    def test_logged_in(self):
        """
        user is logged in, we should not be redirected
        """
        res = self.middleware_callable(self._request_mock())
        self._assert_no_redirect(res)

    def test_login_required(self):
        """
        no user is logged in, we should be redirected to login page
        """
        res = self.middleware_callable(self._request_mock(authenticated=False))
        self._assert_redirect(res, "/accounts/login/?next=/")

    def test_open_url(self):
        """
        case when no user is logged in but we are requesting 'open' url,
        in this case login page, we should not be redirected
        """
        request = self._request_mock(path=urls.reverse("login"),
                                     authenticated=False)
        res = self.middleware_callable(request)
        self._assert_no_redirect(res)


class TestNoProjectsRedirect(MiddlewareTestsMixin, unittest.TestCase):
    """
    test no_projects_redirect() middleware
    """

    # use 'staticmethod' to create unbound function call to middleware factory function,
    # otherwise 'MIDDLEWARE' becomes a class method
    MIDDLEWARE = staticmethod(middleware.no_projects_redirect)

    def test_no_redirect(self):
        """
        case when user have access to a project, we should not be redirected
        :return:
        """
        res = self.middleware_callable(self._request_mock(with_project=True))

        self._assert_no_redirect(res)

    def test_no_project_excluded_url(self):
        """
        case when user have NO project, but is requested one of the excluded
        URLs, e.g. login, we should not be redirected
        """
        request = self._request_mock(path=urls.reverse("login"))
        res = self.middleware_callable(request)
        self._assert_no_redirect(res)

    def test_no_project_redirect(self):
        """
        case when use have NO project and should be redirected to new project page
        """
        res = self.middleware_callable(self._request_mock())

        # check that we were redirected to 'new project' page
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, urls.reverse("new_project"))
