from django import test
from fragview import proj_paths

TEST_PROPS_DIR = "/test/data"


class TestProjPaths(test.TestCase):
    PROPOSAL = "20180479"
    SHIFT = "20190127"
    PROTEIN = "ProteinaseK"

    def test_proposal_dir(self):
        """
        smoke-test of proj_paths.proposal_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}$"

        with self.settings(PROPOSALS_DIR=TEST_PROPS_DIR):
            res = proj_paths.proposal_dir(self.PROPOSAL)
            self.assertRegex(res, expected)

    def test_shift_dir(self):
        """
        smoke-test of proj_paths.shift_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}.*{self.SHIFT}$"

        with self.settings(PROPOSALS_DIR=TEST_PROPS_DIR):
            res = proj_paths.shift_dir(self.PROPOSAL, self.SHIFT)
            self.assertRegex(res, expected)

    def test_protein_dir(self):
        """
        smoke-test of proj_paths.protein_dir()
        """
        expected = f"^{TEST_PROPS_DIR}.*{self.PROPOSAL}.*{self.SHIFT}.*{self.PROTEIN}$"

        with self.settings(PROPOSALS_DIR=TEST_PROPS_DIR):
            res = proj_paths.protein_dir(self.PROPOSAL, self.SHIFT, self.PROTEIN)
            self.assertRegex(res, expected)
