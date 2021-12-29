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


class TestProcessForm(test.TestCase, JobsFormTesterMixin):
    def test_no(self):
        request = self._request(
            dict(
                useDials="on",
                useXdsapp="on",
                spaceGroup="P2",
                cellParams="cellpy",
                friedelLaw="true",
                customXds="cXds",
                customDials="dlsdl",
            )
        )

        form = forms.OldProcessForm(request.POST)
        valid = form.is_valid()
        self.assertTrue(valid)

        self.assertTrue(form.use_dials)
        self.assertFalse(form.use_xds)
        self.assertTrue(form.use_xdsapp)
        self.assertFalse(form.use_autoproc)

        self.assertEqual(form.space_group.short_name, "P2")
        self.assertEqual(form.cell_params, "cellpy")
        self.assertEqual(form.friedel_law, "true")

        self.assertEqual(form.custom_xds, "cXds")
        self.assertEqual(form.custom_autoproc, "")
        self.assertEqual(form.custom_dials, "dlsdl")
        self.assertEqual(form.custom_xdsapp, "")

    def test_invalid_space_group(self):
        """
        test validating request where unknown space groups is specified
        """
        request = self._request(
            dict(
                useDials="on",
                useXdsapp="on",
                spaceGroup="INVALID_GROUP",
                cellParams="cellpy",
                friedelLaw="true",
                customXds="cXds",
                customDials="dlsdl",
            )
        )

        form = forms.OldProcessForm(request.POST)

        # check that it's flagged as invalid
        valid = form.is_valid()
        self.assertFalse(valid)

        # check that correct error was raised
        err = form.errors.get("spaceGroup")
        self.assertEqual(err[0], "unsupported space group 'INVALID_GROUP' specified")


class TestRefineForm(test.TestCase, JobsFormTesterMixin):
    def test_ok(self):
        request = self._request(
            dict(
                useDimple="on",
                spaceGroup="P43",
                pdbModel="32",
                customDimple="ddimp",
            )
        )

        form = forms.OldRefineForm(request.POST)
        valid = form.is_valid()
        self.assertTrue(valid)

        self.assertTrue(form.use_dimple)
        self.assertFalse(form.use_fspipeline)
        self.assertFalse(form.run_aimless)

        self.assertEqual(form.pdb_model, 32)
        self.assertEqual(form.space_group.short_name, "P43")
        self.assertEqual(form.custom_dimple, "ddimp")
        self.assertEqual(form.custom_fspipe, "")

    def test_no_space_group(self):
        """
        test the case where 'run aimless' option is selected,
        but no space group is specified
        """
        request = self._request(
            dict(
                useDimple="on",
                pdbModel="32",
                runAimless="on",
                customDimple="ddimp",
            )
        )

        form = forms.OldRefineForm(request.POST)
        valid = form.is_valid()
        self.assertFalse(valid)

        # check that correct error was raised
        err = form.errors.get("spaceGroup")
        self.assertEqual(err[0], "space group required when aimless is enabled")


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
