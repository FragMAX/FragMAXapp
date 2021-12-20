from typing import List
import unittest
from unittest import mock
from fragview import crystals
from fragview.models import Library, UserProject, Fragment, User
from tests.utils import ProjectTestCase, ViewTesterMixin
from tests.project_setup import Project, DataSet, Crystal
from projects.database import db_session

AR_CSV = """SampleID,FragmentLibrary,FragmentCode
X0000,,
X0001,TSLib,T0
X0002,TSLib,T1
X0003,TSLib,T2
"""

PROTO = "AR"


class TestListProjects(ProjectTestCase, ViewTesterMixin):
    PROJECTS = [
        Project(
            protein="PRT",
            proposal="20180453",
            encrypted=False,
            crystals=[
                Crystal("X01", "TstLib", "VT0"),
            ],
            datasets=[
                DataSet("X01", 1),
            ],
            results=[],
        ),
        Project(
            protein="AST",
            proposal="20284208",
            encrypted=False,
            crystals=[
                Crystal("X02", "TstLib", "VT1"),
            ],
            datasets=[
                DataSet("X02", 1),
            ],
            results=[],
        ),
    ]

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    @db_session
    def test_list(self):

        expected_proj_ids = {proj.id for proj in self.projects}

        resp = self.client.get("/projects/")

        # check listed project by comparing IDs
        listed_proj_ids = {p.id for p in resp.context["projects"]}
        self.assertSetEqual(expected_proj_ids, listed_proj_ids)

        self.assert_contains_template(resp, "projects.html")


class TestNewErrs(unittest.TestCase, ViewTesterMixin):
    def setUp(self):
        self.setup_client()

    def test_get_new_proj_page(self):
        """
        test loading 'new project' page
        """
        resp = self.client.get("/project/new")

        self.assertEqual(200, resp.status_code)
        self.assert_contains_template(resp, "project_new.html")

    def test_new_invalid(self):
        resp = self.client.post("/project/new")

        # we normally fail on crystal CSV first
        self.assert_bad_request(resp, "Could not parse Crystals CSV")


def _crystals_csv_mock():
    # create a mocked 'file-like' object
    csv_file = mock.Mock()
    csv_file.name = "AR.csv"
    csv_file.read.return_value = AR_CSV

    return csv_file


class TestNew(ProjectTestCase, ViewTesterMixin):
    PROJECTS: List = []
    CRYSTALS = [
        crystals.Crystal(
            SampleID="X0000",
            FragmentLibrary=None,
            FragmentCode=None,
        ),
        crystals.Crystal(
            SampleID="X0001",
            FragmentLibrary="TSLib",
            FragmentCode="T0",
        ),
        crystals.Crystal(
            SampleID="X0002",
            FragmentLibrary="TSLib",
            FragmentCode="T1",
        ),
        crystals.Crystal(
            SampleID="X0003",
            FragmentLibrary="TSLib",
            FragmentCode="T2",
        ),
    ]

    def _setup_frags_lib(self):
        library = Library(name="TSLib")
        library.save()

        for n in range(3):
            Fragment(library=library, code=f"T{n}", smiles="C").save()

    def setUp(self):
        super().setUp()
        self.setup_client()
        self._setup_frags_lib()

    @mock.patch("fragview.views.projects.setup_project.delay")
    def test_create_new(self, setup_project_mock):
        resp = self.client.post(
            "/project/new",
            dict(
                protein=PROTO,
                proposal=self.PROP1,
                crystals_csv_file=_crystals_csv_mock(),
            ),
        )

        # check that we got 'ok' response
        self.assert_response(resp, 200, "^ok")

        # check that 'create project' worker was invoked
        # with reasonable arguments
        user_proj = UserProject.objects.get(proposal=self.PROP1)
        setup_project_mock.assert_called_once_with(
            str(user_proj.id),
            PROTO,
            self.PROP1,
            [
                dict(
                    SampleID="X0000",
                    FragmentLibrary=None,
                    FragmentCode=None,
                ),
                dict(
                    SampleID="X0001",
                    FragmentLibrary="TSLib",
                    FragmentCode="T0",
                ),
                dict(
                    SampleID="X0002",
                    FragmentLibrary="TSLib",
                    FragmentCode="T1",
                ),
                dict(
                    SampleID="X0003",
                    FragmentLibrary="TSLib",
                    FragmentCode="T2",
                ),
            ],
            False,
            False,
        )


class TestSetCurrent(ProjectTestCase, ViewTesterMixin):
    PROJECTS = [
        Project(
            protein="PRT",
            proposal="20180453",
            encrypted=False,
            crystals=[],
            datasets=[],
            results=[],
        ),
        Project(
            protein="AST",
            proposal="20284208",
            encrypted=False,
            crystals=[],
            datasets=[],
            results=[],
        ),
    ]

    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)

    @db_session
    def test_set(self):
        resp = self.client.post(f"/project/current/{self.project.id}/")

        # we expected to be redirected to site's root page
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

        # check that current project was stored in the DB
        usr = User.objects.get(id=self.user.id)
        self.assertEqual(usr.current_project.id, self.project.id)

    def test_set_invalid(self):
        invalid_id = 1234
        self.assertFalse(UserProject.objects.filter(id=invalid_id).exists())

        # we should got '404 not found' reply
        resp = self.client.post(f"/project/current/{invalid_id}/")
        self.assertEqual(404, resp.status_code)
