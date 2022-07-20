from itertools import count
import jsonschema
from django import test
from django.test.client import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from fragview import forms
from fragview.models import Library, Fragment
from fragview.tools import Tool
from projects.database import db_session
from tests.utils import ProjectTestCase
from tests.project_setup import Project, Crystal, DataSet, Result

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
        DataSet("TRIM2-x0000", 1),
        DataSet("TRIM2-x0010", 1),
        DataSet("TRIM2-x0011", 1),
        DataSet("TRIM2-x0011", 2),
    ],
    results=[
        Result(
            dataset=("TRIM2-x0000", 1), tool="dimple", input_tool="xds", result="ok"
        ),
        Result(
            dataset=("TRIM2-x0010", 1), tool="dimple", input_tool="xds", result="ok"
        ),
        Result(
            dataset=("TRIM2-x0011", 1), tool="dimple", input_tool="xds", result="ok"
        ),
    ],
)

FRAG_LIB1_CSV = b"""fragmentCode,SMILES
FL1001,O=C1N[C@@H](CO1)C1=CC=CC=C1
FL1002,CN1CCCCS1(=O)=O
FL1002,CC1=CC=C(S1)C1=CC(=NN1)C(O)=O
"""

FRAG_LIB2_CSV = b"""fragmentCode,SMILES
SK001,COC1=CC=C2NC(C)=NC2=C1
SK002,COC(=O)C1CN(C)C(=O)C1
SK003,CC1=CN2C=C(N)C=CC2=N1
SK004,CC(=O)N1CCCCC1CO
"""

FRAG_LIBS = {
    "lib1": FRAG_LIB1_CSV,
    "lib2": FRAG_LIB2_CSV,
}


class TestProcessForm(ProjectTestCase):
    PROJECTS = [PROJECT]

    REQ_JSON = (
        b'{"datasets":["2","3"],'
        b'"tools":[{"id":"dials","customParams":"dialsCust"},{"id":"xds"}],'
        b'"spaceGroup":"P4",'
        b'"cellParams":{"a":143.9,"b":85.5,"c":160.1,"alpha":90,"beta":90,"gamma":90}}'
    )

    REQ_AUTO_JSON = b'{"datasets":["1","3"],"tools":[{"id":"xds"},{"id":"xdsapp"}]}'

    # missing 'tools' property
    REQ_INVALID_JSON = b'{"datasets": ["1", "2"]}'

    def test_invalid(self):
        with self.assertRaisesRegexp(
            jsonschema.exceptions.ValidationError, "'tools' is a required property"
        ):
            forms.ProcessForm(self.project, self.REQ_INVALID_JSON)

    @db_session
    def test_valid(self):
        proc_form = forms.ProcessForm(self.project, self.REQ_JSON)

        # check that we got expected datasets
        dset_ids = set([dset.id for dset in proc_form.datasets])
        self.assertSetEqual(dset_ids, {2, 3})

        # check that we got expected pipelines
        self.assertSetEqual(
            set(proc_form.tools), {(Tool.DIALS, "dialsCust"), (Tool.XDS, "")}
        )

        # check space group
        space_group = proc_form.space_group
        self.assertTrue(space_group.short_name, "P4")

        # check cell parameters
        cell = proc_form.cell_params
        self.assertAlmostEquals(cell.a, 143.9)
        self.assertAlmostEquals(cell.b, 85.5)
        self.assertAlmostEquals(cell.c, 160.1)
        self.assertAlmostEquals(cell.alpha, 90.0)
        self.assertAlmostEquals(cell.beta, 90.0)
        self.assertAlmostEquals(cell.gamma, 90.0)

    @db_session
    def test_valid_auto(self):
        proc_form = forms.ProcessForm(self.project, self.REQ_AUTO_JSON)

        # check that we got expected datasets
        dset_ids = set([dset.id for dset in proc_form.datasets])
        self.assertSetEqual(dset_ids, {1, 3})

        # check that we got expected pipelines
        self.assertSetEqual(set(proc_form.tools), {(Tool.XDS, ""), (Tool.XDSAPP, "")})

        # no space group should be specified
        self.assertIsNone(proc_form.space_group)

        # no cell parameters should be specified
        self.assertIsNone(proc_form.cell_params)


class TestLigfitForm(ProjectTestCase):
    PROJECTS = [PROJECT]

    REQ_JSON = (
        b'{"datasets":[2,3],'
        b'"tools":[{"id":"rhofit"}, {"id":"ligandfit"}],'
        b'"restrains_tool":"grade"}'
    )

    # 'tools' is not an array
    REQ_INVALID_JSON = (
        b'{"datasets": ["1", "2"], "tools": "oink", "restrains_tool": "grade"}'
    )

    def test_invalid(self):
        with self.assertRaisesRegexp(
            jsonschema.exceptions.ValidationError, "'oink' is not of type 'array'"
        ):
            forms.LigfitForm(self.project, self.REQ_INVALID_JSON)

    @db_session
    def test_valid(self):
        ligfit_form = forms.LigfitForm(self.project, self.REQ_JSON)

        # check that we got expected datasets (aka refine result
        dset_ids = set([dset.id for dset in ligfit_form.datasets])
        self.assertSetEqual(dset_ids, {2, 3})

        # check that we got expected tools
        self.assertSetEqual(
            set(ligfit_form.tools), {(Tool.RHOFIT, ""), (Tool.LIGANDFIT, "")}
        )

        # check that we got expected restrains tool
        self.assertEqual(ligfit_form.restrains_tool, Tool.GRADE)


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
    def setup_frag_lib(self):
        lib = Library(name="JBS")
        lib.save()

        for frag_code in ["j001", "j002"]:
            frag = Fragment(library=lib, code=frag_code, smiles="C")
            frag.save()


class TestProjectForm(_SetUpFragLibMixin, ProjectTestCase):
    ReqsFactory = RequestFactory()

    def setUp(self):
        super().setUp()
        self.setup_frag_lib()

    def _request(
        self,
        protein=PROTEIN,
        proposal=PROPOSAL,
        crystals=CRYSTALS_CSV,
        #        frag_libs=FRAG_LIBS,
        frag_libs={},
        autoproc=True,
    ):
        req_args = dict(
            protein=protein,
            proposal=proposal,
            autoproc=autoproc,
        )

        # add fragment libraries to request
        frag_files = {}
        for n, (name, csv) in zip(count(), frag_libs.items()):
            req_args[f"fragsName{n}"] = name
            frag_files[f"fragsCSV{n}"] = SimpleUploadedFile("dmy.csv", csv)

        req = self.ReqsFactory.post(
            "/", req_args  # we don't really care about the URL here
        )

        crystals_file = SimpleUploadedFile(f"{protein}.csv", crystals)
        req.FILES["crystals"] = crystals_file

        # add fragment libraries CSV files to the request
        for name, data in frag_files.items():
            req.FILES[name] = data

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
        (
            protein,
            proposal,
            crystals,
            libraries,
            autoproc,
            encrypt,
        ) = proj_form.get_values()

        self.assertEqual(protein, PROTEIN)
        self.assertEqual(proposal, PROPOSAL)
        self.assertTrue(autoproc)
        self.assertFalse(encrypt)
        self.assertDictEqual(
            libraries,
            {},
        )
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

    def test_valid_with_frags(self):
        """
        test validating a valid form, with custom fragment libraries
        """
        request = self._request(frag_libs=FRAG_LIBS)
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        # check that form validates
        self.assertTrue(proj_form.is_valid())

        # check project settings derived by the form
        (
            protein,
            proposal,
            crystals,
            libraries,
            autoproc,
            encrypt,
        ) = proj_form.get_values()

        self.assertEqual(protein, PROTEIN)
        self.assertEqual(proposal, PROPOSAL)
        self.assertTrue(autoproc)
        self.assertFalse(encrypt)
        self.assertDictEqual(
            libraries,
            {
                "lib1": {
                    "FL1001": "O=C1N[C@@H](CO1)C1=CC=CC=C1",
                    "FL1002": "CC1=CC=C(S1)C1=CC(=NN1)C(O)=O",
                },
                "lib2": {
                    "SK001": "COC1=CC=C2NC(C)=NC2=C1",
                    "SK002": "COC(=O)C1CN(C)C(=O)C1",
                    "SK003": "CC1=CN2C=C(N)C=CC2=N1",
                    "SK004": "CC(=O)N1CCCCC1CO",
                },
            },
        )
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
        the case where invalid crystals CSV is provided
        """
        request = self._request(crystals=b"Foo, bar")
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        # the form should be invalid
        self.assertFalse(proj_form.is_valid())

        # we should get an error about invalid CSV
        self.assertRegex(proj_form.get_error_message(), "^Could not parse Crystals CSV")

    def test_invalid_fraglib_csv(self):
        """
        the case where invalid fragments CSV is provided
        """
        frag_libs = {"dummy": b"fragmentCode,foo"}

        request = self._request(frag_libs=frag_libs)
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        # the form should be invalid
        self.assertFalse(proj_form.is_valid())

        # we should get an error about invalid CSV
        self.assertRegex(
            proj_form.get_error_message(), "^fragments library 'dummy' is invalid"
        )


class TestCrystalsImportForm(_SetUpFragLibMixin, ProjectTestCase):
    ReqsFactory = RequestFactory()

    # crystals CSV, which list unknown fragment library
    INVALID_CSV = b"""SampleID,FragmentLibrary,FragmentCode
MID2-x0017,UnknownLib,UL01
MID2-x0018,UnknownLib,UL02
"""

    def setUp(self):
        super().setUp()
        self.setup_frag_lib()

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
        cryst_form = forms.CrystalsImportForm(self.project, request.POST, request.FILES)

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
        cryst_form = forms.CrystalsImportForm(self.project, request.POST, request.FILES)

        # the form should be invalid
        self.assertFalse(cryst_form.is_valid())

        # we should get an error about invalid CSV
        self.assertRegex(
            cryst_form.get_error_message(),
            r"^Could not parse Crystals CSV\.\nUnknown fragment library",
        )
