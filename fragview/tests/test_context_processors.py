import unittest
from unittest.mock import Mock
from django import test
from django import urls
from fragview import context_processors
from fragview.models import Project

PROP1 = "2020101"
PROP2 = "2020102"


class TestProjectsNoUser(unittest.TestCase):
    """
    test using 'projects' template context processor when no user is logged in
    """
    def test_projects_ctx(self):
        req_mock = Mock()
        req_mock.user.is_authenticated = False

        ctx = context_processors.projects(req_mock)

        # we expect an empty context when user is not authenticated
        self.assertEqual(ctx, {})


class TestProjectsLoggedIn(test.TestCase):
    """
    test using 'projects' template context processor when a user is logged in
    """

    def setUp(self):
        self.proj1 = Project(protein="PRT1", library="LBL1", proposal=PROP1)
        self.proj1.save()

        self.proj2 = Project(protein="PRT2", library="LBL2", proposal=PROP2)
        self.proj2.save()

        #
        # mock a request where user have access to the project created above
        # and current project is set to 'proj1' project
        #
        self.req_mock = Mock()
        self.req_mock.user.is_authenticated = True
        self.req_mock.user.get_current_project.return_value = self.proj1
        self.req_mock.session = dict(proposals=[PROP1, PROP2])

    def test_projects_ctx(self):
        ctx = context_processors.projects(self.req_mock)

        # check that we got expected 'current project' in the context
        self.assertEqual(ctx["project"], self.proj1)

        # check 'user projects' list in the context
        self.assertSetEqual(
            set([self.proj1, self.proj2]),
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
