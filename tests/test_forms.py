from django import test
from django.test.client import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from fragview import forms
from fragview.models import Library, Fragment
from fragview.tools import Tool
from projects.database import db_session
from tests.utils import ProjectTestCase
from tests.project_setup import Project, Crystal, DataSet

PROPOSAL = "12345678"
PROTEIN = "MyProt"
LIBRARY = "JBS"
CRYSTALS_CSV = b"""SampleID,FragmentLibrary,FragmentCode
F001,JBS,j001
F002,JBS,j002
F003,,
"""


PROJECT = Project(
    proposal="20190242",
    protein="TRIM2",
    encrypted=False,
    crystals=[
        Crystal("TRIM2-x0000", None, None),  # Apo crystal
        Crystal("TRIM2-x0010", "VTL", "VT0"),
        Crystal("TRIM2-x0011", "VTL", "VT1"),
        Crystal("TRIM2-x0012", "VTL", "VT2"),
    ],
    datasets=[
        DataSet("TRIM2-x0010", 1),
        DataSet("TRIM2-x0011", 1),
        DataSet("TRIM2-x0011", 2),
    ],
    results=[],
)


class TestProcessForm(ProjectTestCase):
    ReqsFactory = RequestFactory()

    PROJECTS = [PROJECT]

    @db_session
    def test_valid(self):
        request = self.ReqsFactory.post(
            "/",  # we don't really care about the URL here
            dict(
                datasets="2,3",
                pipelines="dials,xds",
                spaceGroup="P4",
                cellParameters="143.9,85.5,160.1,90.0,90.0,90.0",
            ),
        )

        proc_form = forms.ProcessForm(self.project, request.POST)
        self.assertTrue(proc_form.is_valid())

        # check that we got expected datasets
        dset_ids = set([dset.id for dset in proc_form.get_datasets()])
        self.assertSetEqual(dset_ids, {2, 3})

        # check that we got expected pipelines
        self.assertSetEqual(set(proc_form.get_pipelines()), {Tool.DIALS, Tool.XDS})

        # check space group
        space_group = proc_form.get_space_group()
        self.assertTrue(space_group.short_name, "P4")

        # check cell parameters
        cell = proc_form.get_cell_parameters()
        self.assertAlmostEquals(cell.a, 143.9)
        self.assertAlmostEquals(cell.b, 85.5)
        self.assertAlmostEquals(cell.c, 160.1)
        self.assertAlmostEquals(cell.alpha, 90.0)
        self.assertAlmostEquals(cell.beta, 90.0)
        self.assertAlmostEquals(cell.gamma, 90.0)

    @db_session
    def test_valid_auto(self):
        """
        test the case where auto space group and auto cell parameters are specified
        """
        request = self.ReqsFactory.post(
            "/",  # we don't really care about the URL here
            dict(
                datasets="1,3",
                pipelines="xds,xdsapp",
            ),
        )

        proc_form = forms.ProcessForm(self.project, request.POST)
        self.assertTrue(proc_form.is_valid())

        # check that we got expected datasets
        dset_ids = set([dset.id for dset in proc_form.get_datasets()])
        self.assertSetEqual(dset_ids, {1, 3})

        # check that we got expected pipelines
        self.assertSetEqual(set(proc_form.get_pipelines()), {Tool.XDS, Tool.XDSAPP})

        # no space group should be specified
        self.assertIsNone(proc_form.get_space_group())

        # no cell parameters should be specified
        self.assertIsNone(proc_form.get_cell_parameters())


class TestKillJobForm(test.TestCase):
    ReqsFactory = RequestFactory()

    def test_valid(self):
        request = self.ReqsFactory.post(
            "/",  # we don't really care about the URL here
            dict(job_ids="1,4,6"),
        )
        kill_form = forms.KillJobForm(request.POST)

        # validate form request
        self.assertTrue(kill_form.is_valid())

        # check that we got expected job ids
        job_ids = set(kill_form.get_job_ids())
        self.assertSetEqual(job_ids, {"1", "4", "6"})


class _SetUpFragLibMixin:
    def setUp(self):
        lib = Library(name="JBS")
        lib.save()

        for frag_code in ["j001", "j002"]:
            frag = Fragment(library=lib, code=frag_code, smiles="C")
            frag.save()


class TestProjectForm(_SetUpFragLibMixin, test.TestCase):
    ReqsFactory = RequestFactory()

    def _request(
        self,
        protein=PROTEIN,
        proposal=PROPOSAL,
        crystals_csv_data=CRYSTALS_CSV,
        autoproc=True,
    ):
        req = self.ReqsFactory.post(
            "/",  # we don't really care about the URL here
            dict(
                protein=protein,
                proposal=proposal,
                autoproc=autoproc,
            ),
        )

        crystals_file = SimpleUploadedFile(f"{protein}.csv", crystals_csv_data)
        req.FILES["crystals_csv_file"] = crystals_file

        return req

    def test_valid(self):
        """
        test validating a valid form
        """
        request = self._request()
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        # check that form validates
        self.assertTrue(proj_form.is_valid())

        # check project settings derived by the form
        protein, proposal, crystals, autoproc, encrypt = proj_form.get_values()

        self.assertEqual(protein, PROTEIN)
        self.assertEqual(proposal, PROPOSAL)
        self.assertTrue(autoproc)
        self.assertFalse(encrypt)
        self.assertListEqual(
            crystals.as_list(),
            [
                dict(
                    SampleID="F001",
                    FragmentLibrary="JBS",
                    FragmentCode="j001",
                ),
                dict(
                    SampleID="F002",
                    FragmentLibrary="JBS",
                    FragmentCode="j002",
                ),
                dict(
                    SampleID="F003",
                    FragmentLibrary=None,
                    FragmentCode=None,
                ),
            ],
        )

    def test_invalid_crystals_csv(self):
        """
        test validating a valid form
        """
        request = self._request(crystals_csv_data=b"Foo, bar")
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        # the form should be invalid
        self.assertFalse(proj_form.is_valid())

        # we should get an error about invalid CSV
        self.assertRegex(proj_form.get_error_message(), "^Could not parse Crystals CSV")


class TestCrystalsImportForm(_SetUpFragLibMixin, test.TestCase):
    ReqsFactory = RequestFactory()

    # crystals CSV, which list unknown fragment library
    INVALID_CSV = b"""SampleID,FragmentLibrary,FragmentCode
MID2-x0017,UnknownLib,UL01
MID2-x0018,UnknownLib,UL02
"""

    def _request(
        self,
        crystals_csv_data=CRYSTALS_CSV,
    ):
        req = self.ReqsFactory.post(
            "/",  # we don't really care about the URL here
        )

        crystals_file = SimpleUploadedFile(f"new.csv", crystals_csv_data)
        req.FILES["crystals_csv_file"] = crystals_file

        return req

    def test_valid(self):
        """
        test validating a valid form
        """
        request = self._request()
        cryst_form = forms.CrystalsImportForm(request.POST, request.FILES)

        # check that form validates
        self.assertTrue(cryst_form.is_valid())

        # check that CSV was parsed correctly
        crystals = cryst_form.get_crystals()
        self.assertListEqual(
            crystals.as_list(),
            [
                dict(
                    SampleID="F001",
                    FragmentLibrary="JBS",
                    FragmentCode="j001",
                ),
                dict(
                    SampleID="F002",
                    FragmentLibrary="JBS",
                    FragmentCode="j002",
                ),
                dict(
                    SampleID="F003",
                    FragmentLibrary=None,
                    FragmentCode=None,
                ),
            ],
        )

    def test_invalid_crystals_csv(self):
        """
        test validating a valid form
        """
        request = self._request(crystals_csv_data=self.INVALID_CSV)
        cryst_form = forms.CrystalsImportForm(request.POST, request.FILES)

        # the form should be invalid
        self.assertFalse(cryst_form.is_valid())

        # we should get an error about invalid CSV
        self.assertRegex(
            cryst_form.get_error_message(),
            r"^Could not parse Crystals CSV\.\nUnknown fragment library",
        )
