from unittest.mock import Mock
from django import test
from fragview import projects
from fragview.models import User, Project, Library

TEST_PROPS_DIR = "/test/data"


class TestFuncs(test.TestCase):
    PROPOSAL = "20180479"
    SHIFT = "20190127"
    PROTEIN = "ProteinaseK"

    def test_proposal_dir(self):
        """
        smoke-test of proj_paths.proposal_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}$"

        with self.settings(PROPOSALS_DIR=TEST_PROPS_DIR):
            res = projects.proposal_dir(self.PROPOSAL)
            self.assertRegex(res, expected)

    def test_shift_dir(self):
        """
        smoke-test of proj_paths.shift_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}.*{self.SHIFT}$"

        with self.settings(PROPOSALS_DIR=TEST_PROPS_DIR):
            res = projects.shift_dir(self.PROPOSAL, self.SHIFT)
            self.assertRegex(res, expected)

    def test_protein_dir(self):
        """
        smoke-test of proj_paths.protein_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}.*{self.SHIFT}.*{self.PROTEIN}$"

        with self.settings(PROPOSALS_DIR=TEST_PROPS_DIR):
            res = projects.protein_dir(self.PROPOSAL, self.SHIFT, self.PROTEIN)
            self.assertRegex(res, expected)


class TestCurrentProject(test.TestCase):
    """
    test projects.current_project()
    """
    USERNAME = "puser"
    PROJ_PROPOSAL = "20140001"
    OTHER_PROPOSAL = "20209988"

    def setUp(self):
        lib = Library(name="ad")
        lib.save()

        self.proj = Project(proposal=self.PROJ_PROPOSAL, library=lib)
        self.proj.save()

        self.user = User(current_project=self.proj)
        self.user.save()

    def _setup_request_mock(self, user_proposals):
        request = Mock()
        request.user = self.user
        request.session = dict(proposals=user_proposals)

        return request

    def test_current_project(self):
        request = self._setup_request_mock([self.PROJ_PROPOSAL])

        cur_proj = projects.current_project(request)
        self.assertEqual(self.proj.id, cur_proj.id)

    def test_current_project_no_access(self):
        """
        test the case when user is not a part of it's current
        project's proposal
        """
        request = self._setup_request_mock([self.OTHER_PROPOSAL])

        self.assertIsNone(projects.current_project(request))
