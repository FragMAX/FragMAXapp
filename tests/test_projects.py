from unittest.mock import Mock, patch
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

        with patch("fragview.projects.SITE") as site:
            site.PROPOSALS_DIR = TEST_PROPS_DIR

            res = projects.proposal_dir(self.PROPOSAL)
            self.assertRegex(res, expected)

    def test_shift_dir(self):
        """
        smoke-test of proj_paths.shift_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}.*{self.SHIFT}$"

        with patch("fragview.projects.SITE") as site:
            site.PROPOSALS_DIR = TEST_PROPS_DIR

            res = projects.shift_dir(self.PROPOSAL, self.SHIFT)
            self.assertRegex(res, expected)

    def test_protein_dir(self):
        """
        smoke-test of proj_paths.protein_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}.*{self.SHIFT}.*{self.PROTEIN}$"

        with patch("fragview.projects.SITE") as site:
            site.PROPOSALS_DIR = TEST_PROPS_DIR

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


class TestParseDatasetName(test.TestCase):
    """
    test parse_dataset_name() function
    """

    def _check(self, dataset, expected_sample, expected_run):
        sample, run = projects.parse_dataset_name(dataset)
        self.assertEqual(sample, expected_sample)
        self.assertEqual(run, expected_run)

    def test_func(self):
        self._check("Nsp10-VT00224_1", "Nsp10-VT00224", "1")
        self._check("Nsp10-SBX17160_4", "Nsp10-SBX17160", "4")
        self._check("Nsp10-361_5d_3_1", "Nsp10-361_5d_3", "1")
