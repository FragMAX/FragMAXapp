from django import test
from django.test.client import RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from fragview import forms
from fragview.models import Library, Fragment


PROPOSAL = "12345678"
PROTEIN = "MyProt"
LIBRARY = "JBS"
CRYSTALS_CSV = b"""SampleID,FragmentLibrary,FragmentCode
F001,JBS,j001
F002,JBS,j002
F003,,
"""


class JobsFormTesterMixin:
    DS_FILTER = "set1,set2"
    ReqsFactory = RequestFactory()

    def _request(self, args):
        return self.ReqsFactory.post(
            # we don't really care about the URL here
            "/",
            args,
        )


class TestLigfitForm(test.TestCase, JobsFormTesterMixin):
    def test_rho_fit(self):
        request = self._request(dict(useRhoFit="on"))

        form = forms.LigfitForm(request.POST)

        valid = form.is_valid()
        self.assertTrue(valid)
        self.assertTrue(form.use_rho_fit)
        self.assertFalse(form.use_phenix_ligfit)

    def test_use_both(self):
        request = self._request(
            dict(
                datasetsFilter=self.DS_FILTER,
                useRhoFit="on",
                usePhenixLigfit="on",
                customLigFit="cLigFit",
                customRhoFit="cRhoFit",
                cifMethod="grade",
            )
        )

        form = forms.LigfitForm(request.POST)

        valid = form.is_valid()
        self.assertTrue(valid)
        self.assertEqual(form.datasets_filter, self.DS_FILTER)
        self.assertTrue(form.use_rho_fit)
        self.assertTrue(form.use_phenix_ligfit)
        self.assertEqual(form.custom_ligfit, "cLigFit")
        self.assertEqual(form.custom_rhofit, "cRhoFit")
        self.assertEqual(form.cif_method, "grade")


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
