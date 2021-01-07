import unittest
from unittest.mock import Mock
from django import test
from django import urls
from fragview import context_processors
from fragview.models import Project, Library

PROP1 = "2020101"
PROP2 = "2020102"


def _get_request_mock(is_authenticated, current_project=None, session=None):
    req = Mock()
    req.user.is_authenticated = is_authenticated

    if current_project is not None:
        req.user.get_current_project.return_value = current_project

    if session is not None:
        req.session = session

    return req


class TestSite(unittest.TestCase):
    """
    test 'site' template context processor
    """
    def test_logged_in(self):
        """
        check context generated when user is logged in
        """
        ctx = context_processors.site(_get_request_mock(True))

        # check that we got "site_logo" image specified
        self.assertIn("site_logo", ctx)

        # check that we got a dictionary of disabled features
        self.assertIsInstance(ctx["disabled"], dict)

    def test_no_user(self):
        """
        check context generated when no user is logged in
        """
        ctx = context_processors.site(_get_request_mock(False))

        # we should have an 'account style' specified
        self.assertIn("account_style", ctx)


class TestProjectsNoUser(unittest.TestCase):
    """
    test using 'projects' template context processor when no user is logged in
    """
    def test_projects_ctx(self):
        ctx = context_processors.projects(_get_request_mock(False))

        # we expect an empty context when user is not authenticated
        self.assertEqual(ctx, {})


class TestProjectsLoggedIn(test.TestCase):
    """
    test using 'projects' template context processor when a user is logged in
    """

    def setUp(self):
        lib1 = Library(name="LIB1")
        lib1.save()
        self.proj1 = Project(protein="PRT1", library=lib1, proposal=PROP1)
        self.proj1.save()

        lib2 = Library(name="LIB2")
        lib2.save()
        self.proj2 = Project(protein="PRT2", library=lib2, proposal=PROP2)
        self.proj2.save()

        #
        # mock a request where user have access to the project created above
        # and current project is set to 'proj1' project
        #
        self.req_mock = _get_request_mock(True,
                                          current_project=self.proj1,
                                          session=dict(proposals=[PROP1, PROP2]))

    def test_projects_ctx(self):
        ctx = context_processors.projects(self.req_mock)

        # check that we got expected 'current project' in the context
        self.assertEqual(ctx["project"], self.proj1)

        # check 'user projects' list in the context
        self.assertSetEqual(
            {self.proj1, self.proj2},
            set(ctx["projects"]))


class TestActiveMenu(unittest.TestCase):
    """
    test 'active menu' template context processor, the processor
    that sets the 'active_menu' template context variable
    """
    def setup_req_mock(self, url):
        req_mock = Mock()
        req_mock.path_info = url

        return req_mock

    def test_no_menu(self):
        """
        test some URLs where there should be no active menu
        """
        no_menu_urls = ["/foo", "/bar", "/projects", urls.reverse("datasets")]
        for url in no_menu_urls:
            ctx = context_processors.active_menu(self.setup_req_mock(url))
            self.assertDictEqual({}, ctx)

    def test_project_menu(self):
        """
        test URLs where 'project' menu is active
        """
        project_urls = ["/", "/pdbs", "/pdb/242", "/pdb/add"]
        for url in project_urls:
            ctx = context_processors.active_menu(self.setup_req_mock(url))
            self.assertDictEqual(dict(active_menu="project"), ctx)
