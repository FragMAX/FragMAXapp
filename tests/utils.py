from typing import List
from os import path
from pathlib import Path
import unittest
from unittest.mock import ANY
import shutil
import tempfile
from fragview import auth
from django import test
from fragview.projects import get_project
from fragview.models import UserProject
from projects.database import db_session
from tests.project_setup import create_temp_project, Project


def identity(func):
    return func


class WorkerTaskTester(unittest.TestCase):
    def assert_locking(self, red_lock_mock, lock_id):
        """
        make assertions that a RedLock with specified id was acquired and released
        """
        red_lock_mock.assert_called_once_with(lock_id, [ANY])

        lock = red_lock_mock.return_value
        lock.acquire.assert_called_once_with()
        lock.release.assert_called_once_with()


class ViewTesterMixin:
    """
    Utility mixin, that provides method to setup authenticated HTTP client
    """

    PROP1 = "20180201"
    PROP2 = "20170223"

    PROJECT1 = Project(
        protein="PrtK",
        proposal=PROP1,
        encrypted=False,
        datasets=[],
        crystals=[],
        results=[],
    )

    def setup_client(self, user_proposals: List[str] = []):
        """
        setup test HTTP client which is logged in with a user 'dummy'
        that have access to PROP1 and PROP2 proposals
        """
        self.user = auth.ISPyBBackend()._get_user_obj("dummy")
        self.client = test.Client()
        self.client.force_login(user=self.user)

        session = self.client.session
        session["proposals"] = user_proposals
        session.save()

    def set_current_project(self, project_id: str):
        proj = UserProject.get_project(self.proposals, project_id)  # type: ignore
        self.user.set_current_project(proj)

    def assert_contains_template(self, response, template_name):
        """
        assert that the response rendering involved using the specified template
        """
        templ_names = [t.name for t in response.templates]
        self.assertIn(template_name, templ_names)

    def assert_response(self, response, status_code, content_regexp):
        self.assertEquals(response.status_code, status_code)
        self.assertRegex(response.content.decode(), content_regexp)

    def assert_response_equals(self, response, status_code, content, content_type):
        """
        assert exact match of response's status code, content body and content-type header
        """
        self.assertEquals(response.status_code, status_code)
        self.assertEquals(response.content, content)
        self.assertEquals(response["content-type"], content_type)

    def assert_file_response(self, response, content):
        self.assertEquals(response.status_code, 200)
        self.assertTrue(response.streaming)
        resp_content = b"".join(response.streaming_content)
        self.assertEquals(resp_content, content)

    def assert_bad_request(self, response, error_msg):
        self.assert_response(response, 400, error_msg)

    def assert_not_found_response(self, response, error_msg):
        self.assert_response(response, 404, error_msg)


class TempDirMixin:
    def setup_temp_dir(self):
        self.temp_dir = tempfile.mkdtemp()

    def tear_down_temp_dir(self):
        shutil.rmtree(self.temp_dir)


class ProjectTestCase(test.TestCase, TempDirMixin):
    """
    Sets-up mocked project(s) in temp directories
    and override settings to redirect code to use
    these projects.

    Used for tests on the code that needs to access project
    data, such as many views, etc.

    For test case what need to set-up custom projects,
    the 'PROJECTS' class field can be overridden.

    After setUp() call following properties are available:

    self.project           - first created project
    self.projects          - all projects created
    self.proposals         - above projects proposals
    self.projects_root_dir - projects root directory
    self.projects_db_dir   - directory where project's database files go
    """

    # default temp project
    PROJECTS: List[Project] = [
        Project(
            protein="Nsp5",
            proposal="20180453",
            encrypted=False,
            datasets=[],
            crystals=[],
            results=[],
        )
    ]

    @property
    def proposals(self) -> List[str]:
        """
        list of proposals for all created projects
        """
        with db_session:
            return [proj.proposal for proj in self.projects]

    @property
    def project(self):
        """
        convenience property to get 'first' project
        """
        return self.projects[0]

    @db_session
    def get_user_project(self, project) -> UserProject:
        return UserProject.get(project.id)

    @db_session
    def add_pdb(self, filename: str):
        """
        add 'PDB' entry to 'first' project
        """
        return self.project.db.PDB(filename=filename)

    @db_session
    def forget_key(self):
        with db_session:
            project = get_project(self.projects_db_dir, self.project.id)
            project.forget_key()

    def _setup_temp_project(self):
        self.projects = []
        for project in self.PROJECTS:
            self.projects.append(create_temp_project(self.projects_db_dir, project))

    def setUp(self):
        self.setup_temp_dir()

        # set-up project(s) database(s)
        self.projects_db_dir = Path(self.temp_dir, "db", "projs")
        self._setup_temp_project()

        # set-up temp project root directory
        self.projects_root_dir = Path(self.temp_dir, "fragmax")
        self.projects_root_dir.mkdir()

        # override path to projects database dir
        self.settings_override = self.settings(
            PROJECTS_DB_DIR=self.projects_db_dir,
            PROJECTS_ROOT_DIR=self.projects_root_dir,
        )
        self.settings_override.enable()

    def tearDown(self):
        # restore original settings
        self.settings_override.disable()
        # clean-up
        self.tear_down_temp_dir()


def data_file_path(file_name) -> Path:
    """
    return absolute path specified file in tests 'data' directory
    """
    return Path(path.dirname(__file__), "data", file_name)


def xs_data_path(num) -> Path:
    return data_file_path(f"xs_data{num}.xml")
