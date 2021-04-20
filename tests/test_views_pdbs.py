import unittest
from io import BytesIO
from unittest.mock import patch, Mock
from django import test
from django.urls import reverse
from fragview.views import pdbs
from fragview.models import Project, Library, PDB
from tests.utils import ViewTesterMixin


def _add_pdbs(project):
    pdb1 = PDB(project=project, filename="foo.pdb")
    pdb1.save()

    pdb2 = PDB(project=project, filename="bar.pdb")
    pdb2.save()

    return [pdb1, pdb2]


class _PDBViewTester(test.TestCase, ViewTesterMixin):
    def setUp(self):
        self.setup_client()
        self.setup_project()


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


class TestAddPdbEntry(test.TestCase):
    """
    test _add_pdb_entry() function
    """

    PDB_NAME = "9876.pdb"

    def test_duplicate_entry(self):
        lib = Library(name="JBS")
        lib.save()

        proj = Project(
            protein="PRT", library=lib, proposal="20210102", shift="20190808"
        )
        proj.save()

        pdbs._add_pdb_entry(proj, self.PDB_NAME)

        with self.assertRaisesRegex(
            pdbs.PDBAddError, "^Model file '9876.pdb' already exists in the project."
        ):
            pdbs._add_pdb_entry(proj, self.PDB_NAME)


class TestListView(_PDBViewTester):
    """
    test 'manage PDBs' view
    """

    def test_no_pdbs(self):
        """
        the case when project does not have any PDBs
        """
        resp = self.client.get(reverse("manage_pdbs"))

        # check template used
        self.assert_contains_template(resp, "fragview/pdbs.html")

        # check that PDBs list is empty
        self.assertEqual(resp.context["pdbs"].count(), 0)

    def test_have_pdbs(self):
        """
        the case when project have a couple of PDBs
        """
        pdbs = _add_pdbs(self.proj)

        resp = self.client.get(reverse("manage_pdbs"))

        # check template used
        self.assert_contains_template(resp, "fragview/pdbs.html")

        # check that we get the expected PDBs listed
        self.assertSetEqual(set(resp.context["pdbs"]), set(pdbs))


class TestAddView(_PDBViewTester):
    """
    test 'Add new PDB' page view
    """

    def test_add(self):
        resp = self.client.get("/pdb/add")

        # check template used
        self.assert_contains_template(resp, "fragview/add_pdb.html")


class TestEditView(_PDBViewTester):
    """
    test 'PDB edit' view, that is the view that is
    used to show some PDB info and to delete PDBs
    """

    def test_info_page(self):
        """
        test loading the 'PDB info' page
        """
        pdb = PDB(project=self.proj, filename="moin.pdb")
        pdb.save()

        resp = self.client.get(f"/pdb/{pdb.id}")

        # check template used
        self.assert_contains_template(resp, "fragview/pdb.html")

        # check that PDB in the context is correct one
        self.assertEqual(resp.context["pdb"].id, pdb.id)

    def test_pdb_not_found(self):
        """
        test loading 'PDB info' page for unknown PDB
        """
        resp = self.client.get("/pdb/123")

        self.assertEqual(404, resp.status_code)

    @patch("os.remove")
    def test_delete(self, remove_mock):
        """
        test deleting PDB
        """
        # add PDB to our project
        pdb = PDB(project=self.proj, filename="moin.pdb")
        pdb.save()
        pdb_file = pdb.file_path()

        # make the 'delete' request
        resp = self.client.post(f"/pdb/{pdb.id}")

        # check that PDB is removed from the database,
        # e.g. that our project does not have any PDBs
        self.assertEqual(PDB.project_pdbs(self.proj).count(), 0)

        # check redirect response
        self.assertEqual(302, resp.status_code)
        self.assertEqual(reverse("manage_pdbs"), resp.url)

        # check call to mock
        remove_mock.assert_called_once_with(pdb_file)


class TestGetView(_PDBViewTester):
    DATA = b"orange vs kiwi"

    def test_unknown_id(self):
        resp = self.client.post("/pdb/get/42")
        self.assert_not_found_response(resp, ".")

    def test_success(self):
        pdb = PDB(project=self.proj, filename="foo.pdb")
        pdb.save()

        with patch("fragview.views.utils.open") as open_mock:
            open_mock.return_value = BytesIO(self.DATA)

            resp = self.client.post(f"/pdb/get/{pdb.id}")

        self.assert_file_response(resp, self.DATA)


class TestNewView(_PDBViewTester):
    PDB_FILE = "1AB2.pdb"
    PDB_ID = "2ID3"
    PDB_DATA = b"fake-mews"

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
        save_pdb_mock.assert_called_once_with(
            self.proj, None, self.PDB_FILE, self.PDB_DATA
        )

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
                self.proj, self.PDB_ID, f"{self.PDB_ID}.pdb", fetch_mock.return_value
            )

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
