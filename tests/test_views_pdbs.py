import unittest
from io import BytesIO
from unittest.mock import patch, Mock, ANY
from django import test
from django.urls import reverse
from fragview.views import pdbs
from projects.database import db_session, commit
from tests.utils import ViewTesterMixin, ProjectTestCase, data_file_path


class _PDBViewTester(ProjectTestCase, ViewTesterMixin):
    def setUp(self):
        super().setUp()
        self.setup_client(self.proposals)


class TestIsValidPDBFilename(unittest.TestCase):
    """
    test _is_valid_pdb_filename() function
    """

    def test_valids(self):
        self.assertTrue(pdbs._is_valid_pdb_filename("2ID8.pdb"))
        self.assertTrue(pdbs._is_valid_pdb_filename("0000.PDB"))
        self.assertTrue(pdbs._is_valid_pdb_filename("abcd.pdb"))
        # mixed cases, check that cases are ignored
        self.assertTrue(pdbs._is_valid_pdb_filename("MySpecialModel.PdB"))

    def test_invalids(self):
        self.assertFalse(pdbs._is_valid_pdb_filename(""))
        # wrong file extension
        self.assertFalse(pdbs._is_valid_pdb_filename("2ID8.gif"))
        # invalid characters
        self.assertFalse(pdbs._is_valid_pdb_filename("No_or-please.pdb"))


class TestSavePdb(_PDBViewTester):
    """
    test _save_pdb()
    """

    # PDB_NAME = "9876.pdb"
    PDB_NAME = "SHP2.pdb"

    def setUp(self):
        super().setUp()

        # load PDB file
        self.pdb_data = data_file_path(self.PDB_NAME).read_bytes()

    def assert_pdb(self, pdb, pdb_id=""):
        self.assertEqual(pdb.filename, self.PDB_NAME)
        self.assertEqual(pdb.pdb_id, pdb_id)
        self.assertEqual(pdb.space_group, "C 2 2 21")
        self.assertAlmostEqual(pdb.unit_cell_a, 43.861)
        self.assertAlmostEqual(pdb.unit_cell_b, 85.539)
        self.assertAlmostEqual(pdb.unit_cell_c, 160.111)
        self.assertAlmostEqual(pdb.unit_cell_alpha, 90.0)
        self.assertAlmostEqual(pdb.unit_cell_beta, 90.0)
        self.assertAlmostEqual(pdb.unit_cell_gamma, 90.0)

    @db_session
    def test_ok(self):
        pdbs._save_pdb(self.project, None, self.PDB_NAME, self.pdb_data)

        #
        # check that correct pdb entry was created
        #
        proj_pdbs = list(self.project.get_pdbs())
        self.assertEqual(len(proj_pdbs), 1)
        self.assert_pdb(proj_pdbs[0])

    @db_session
    def test_with_pdb_id(self):
        PDB_ID = "2ID8"
        pdbs._save_pdb(self.project, PDB_ID, self.PDB_NAME, self.pdb_data)

        #
        # check that correct pdb entry was created
        #
        proj_pdbs = list(self.project.get_pdbs())
        self.assertEqual(len(proj_pdbs), 1)
        self.assert_pdb(proj_pdbs[0], pdb_id=PDB_ID)

    def test_duplicate_entry(self):
        with db_session:
            pdbs._save_pdb(self.project, None, self.PDB_NAME, self.pdb_data)

        with db_session:
            with self.assertRaisesRegex(
                pdbs.PDBAddError,
                f"^Model file '{self.PDB_NAME}' already exists in the project.",
            ):
                pdbs._save_pdb(self.project, None, self.PDB_NAME, self.pdb_data)

    @db_session
    def test_invalid_pdb(self):
        with self.assertRaisesRegex(
            pdbs.PDBAddError,
            f"^Failed to read space group",
        ):
            pdbs._save_pdb(self.project, None, "Foo.pdb", b"bah")


class TestListView(_PDBViewTester):
    """
    test 'manage PDBs' view
    """

    @db_session
    def test_no_pdbs(self):
        """
        the case when project does not have any PDBs
        """
        resp = self.client.get(reverse("manage_pdbs"))

        # check template used
        self.assert_contains_template(resp, "pdbs.html")


class TestAddView(_PDBViewTester):
    """
    test 'Add new PDB' page view
    """

    @db_session
    def test_add(self):
        resp = self.client.get("/pdb/add")

        # check template used
        self.assert_contains_template(resp, "pdb_add.html")


class TestEditView(_PDBViewTester):
    """
    test 'PDB edit' view, that is the view that is
    used to show some PDB info and to delete PDBs
    """

    def test_info_page(self):
        """
        test loading the 'PDB info' page
        """
        pdb = self.add_pdb("moin.pdb")

        with db_session:
            resp = self.client.get(f"/pdb/{pdb.id}")

            # check template used
            self.assert_contains_template(resp, "pdb.html")

            # check that PDB in the context is correct one
            self.assertEqual(resp.context["pdb"].id, pdb.id)

    @db_session
    def test_pdb_not_found(self):
        """
        test loading 'PDB info' page for unknown PDB
        """
        resp = self.client.get("/pdb/123")

        self.assertEqual(404, resp.status_code)

    @patch("pathlib.Path.unlink")
    def test_delete(self, unlink_mock):
        """
        test deleting PDB
        """
        # add PDB to our project
        pdb = self.add_pdb("main.pdb")

        with db_session:
            # make the 'delete' request
            resp = self.client.post(f"/pdb/{pdb.id}")
            commit()

            # check that PDB is removed from the database,
            # e.g. that our project does not have any PDBs
            self.assertIsNone(self.project.get_pdb(pdb.id))

            # check redirect response
            self.assertEqual(302, resp.status_code)
            self.assertEqual(reverse("manage_pdbs"), resp.url)

            # check call to mock
            unlink_mock.assert_called()


class TestGetView(_PDBViewTester):
    DATA = b"orange vs kiwi"

    @db_session
    def test_unknown_id(self):
        resp = self.client.post("/pdb/get/42")
        self.assert_not_found_response(resp, ".")

    def test_success(self):
        pdb = self.add_pdb("foo.pdb")

        with db_session:
            with patch("fragview.views.utils.open") as open_mock:
                open_mock.return_value = BytesIO(self.DATA)
                resp = self.client.post(f"/pdb/get/{pdb.id}")

        self.assert_file_response(resp, self.DATA)


class TestNewView(_PDBViewTester):
    PDB_FILE = "1AB2.pdb"
    PDB_ID = "2ID3"
    PDB_DATA = b"fake-mews"

    @db_session
    @patch("fragview.views.pdbs._save_pdb")
    def test_upload_file(self, save_pdb_mock):
        """
        test uploading adding local PDB file
        """
        # create a mocked 'file-like' object
        pdb_file = Mock()
        pdb_file.name = self.PDB_FILE
        pdb_file.read.return_value = self.PDB_DATA

        resp = self.client.post("/pdb/new", dict(method="upload_file", pdb=pdb_file))

        # check for OK response
        self.assertEqual(200, resp.status_code)

        # check that _save_pdb() was called with correct args
        save_pdb_mock.assert_called_once_with(ANY, None, self.PDB_FILE, self.PDB_DATA)
        proj_arg = save_pdb_mock.call_args[0][0]
        self.assertEqual(proj_arg.id, self.project.id)

    @db_session
    @patch("fragview.views.pdbs._save_pdb")
    def test_fetch_online(self, save_pdb_mock):
        """
        test the case when PDB is fetched online from RCSB database
        """
        with patch("fragview.views.pdbs._fetch_from_rcsb") as fetch_mock:
            resp = self.client.post(
                "/pdb/new", dict(method="fetch_online", pdb_id=self.PDB_ID)
            )

            # check for OK response
            self.assertEqual(200, resp.status_code)

            # check that _fetch_from_rcsb() was called with correct args
            fetch_mock.assert_called_once_with(self.PDB_ID)

            # check that _save_pdb() was called with correct args
            save_pdb_mock.assert_called_once_with(
                ANY, self.PDB_ID, f"{self.PDB_ID}.pdb", fetch_mock.return_value
            )
            proj_arg = save_pdb_mock.call_args[0][0]
            self.assertEqual(proj_arg.id, self.project.id)

    @db_session
    def test_invalid_new(self):
        """
        test the case of uploading PDB file with invalid file name
        """
        # create a mocked 'file-like' object
        pdb_file = Mock()
        pdb_file.name = "is-invalid.bnx"

        resp = self.client.post("/pdb/new", dict(method="upload_file", pdb=pdb_file))

        # we should get 'Bad request, Invalid PDB filename' response
        self.assertEqual(400, resp.status_code)
        self.assertRegexpMatches(resp.content.decode(), "^Invalid PDB filename")


@patch("pypdb.get_pdb_file")
class TestFetchFromRCSB(test.TestCase):
    """
    test _fetch_from_rcsb() function
    """

    PDB_ID = "1XY8"
    PDB_CONTENT = "dummy-pdb-content"

    def test_ok(self, get_pdb_mock):
        """
        test when we successfully fetch PDB from RCSB
        """
        get_pdb_mock.return_value = self.PDB_CONTENT

        # fetch from RCSB
        data = pdbs._fetch_from_rcsb(self.PDB_ID)

        # check results and calls
        self.assertEqual(data.decode(), self.PDB_CONTENT)
        get_pdb_mock.assert_called_once_with(self.PDB_ID, filetype="pdb")

    def test_pdb_not_found(self, get_pdb_mock):
        """
        test when PDB with specified ID is not found
        """
        get_pdb_mock.return_value = None

        with self.assertRaisesRegex(pdbs.PDBAddError, "^no PDB with ID '1XY8' found"):
            pdbs._fetch_from_rcsb(self.PDB_ID)
