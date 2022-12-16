import unittest
from unittest.mock import Mock
from pathlib import Path
from django import urls
from fragview import context_processors
from fragview.models import UserProject
from tests.project_setup import Project
from tests.utils import ProjectTestCase

PROP1 = "2020101"
PROP2 = "2020102"

PROJECT1 = Project(
    protein="Nsp12",
    proposal=PROP1,
    crystals=[],
    datasets=[],
    results=[],
)

PROJECT2 = Project(
    protein="AR",
    proposal=PROP2,
    crystals=[],
    datasets=[],
    results=[],
)


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


class TestProjectsLoggedIn(ProjectTestCase):
    """
    test using 'projects' template context processor when a user is logged in
    """

    PROJECTS = [PROJECT1, PROJECT2]

    def setUp(self):
        super().setUp()

        #
        # set-up two dummy projects
        #
        self.proj_db_dir = Path(self.temp_dir, "db", "projs")
        self.proj1 = self.projects[0]
        self.user_proj1 = UserProject.get(self.proj1.id)
        self.proj2 = self.projects[1]

        #
        # mock a request where user have access to the project created above
        # and current project is set to 'proj1' project
        #
        self.req_mock = _get_request_mock(
            True,
            current_project=self.user_proj1,
            session=dict(proposals=[PROP1, PROP2]),
        )

    def tearDown(self):
        self.tear_down_temp_dir()

    def test_projects_ctx(self):
        ctx = context_processors.projects(self.req_mock)

        # check that we got expected 'current project' in the context
        self.assertEqual(ctx["project"], self.user_proj1)

        # check 'user's projects' list in the context
        got_proj_ids = {proj.id for proj in ctx["projects"]}
        self.assertSetEqual({self.proj1.id, self.proj2.id}, got_proj_ids)


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
