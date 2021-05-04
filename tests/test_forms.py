from os import path
import unittest
from unittest import mock
from django import test
from django.test.client import RequestFactory
from fragview import forms
from fragview.sites import SITE
from django.core.files.uploadedfile import SimpleUploadedFile
from fragview import projects
from fragview.models import Project


PROPOSAL = "12345678"
PROTEIN = "MyProt"
LIBRARY = "JBS"
SHIFT_1 = "00000001"
SHIFT_2 = "00000002"


def is_dir_mock(non_exist_dir):
    """
    construct an 'os.path.isdir()' mock, which returns
    false for the 'non_exist_dir' path, and true otherwise
    """

    def _isdir(dir):
        return dir != non_exist_dir

    return _isdir


class ProjFormTesterMixin:
    """
    Utility Mixin for testing Project Form class
    """

    ReqsFactory = RequestFactory()

    def _request(
        self,
        protein=PROTEIN,
        library_name=LIBRARY,
        root=PROPOSAL,
        subdirs=f"{SHIFT_1},{SHIFT_2}",
        fragmenst_file_data="B2a,N#Cc1c(cccc1)O",
        encrypted=False,
    ):

        req = self.ReqsFactory.post(
            "/",  # we don't really care about the URL here
            dict(
                protein=protein,
                library_name=library_name,
                root=root,
                subdirs=subdirs,
                encrypted=encrypted,
            ),
        )

        frags_file = SimpleUploadedFile("frags.csv", fragmenst_file_data.encode())
        req.FILES["fragments_file"] = frags_file

        return req


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


class TestProcessForm(test.TestCase, JobsFormTesterMixin):
    def test_form(self):
        request = self._request(
            dict(
                useDials="on",
                useXdsapp="on",
                spaceGroup="SGRP",
                cellParams="cellpy",
                friedelLaw="true",
                customXds="cXds",
                customDials="dlsdl",
            )
        )

        form = forms.ProcessForm(request.POST)
        valid = form.is_valid()
        self.assertTrue(valid)

        self.assertTrue(form.use_dials)
        self.assertFalse(form.use_xds)
        self.assertTrue(form.use_xdsapp)
        self.assertFalse(form.use_autoproc)

        self.assertEqual(form.space_group, "SGRP")
        self.assertEqual(form.cell_params, "cellpy")
        self.assertEqual(form.friedel_law, "true")

        self.assertEqual(form.custom_xds, "cXds")
        self.assertEqual(form.custom_autoproc, "")
        self.assertEqual(form.custom_dials, "dlsdl")
        self.assertEqual(form.custom_xdsapp, "")


class TestRefineForm(test.TestCase, JobsFormTesterMixin):
    def test_form(self):
        request = self._request(
            dict(
                useDimple="on",
                refSpaceGroup="SGRP",
                pdbModel="32",
                customDimple="ddimp",
            )
        )

        form = forms.RefineForm(request.POST)
        valid = form.is_valid()
        self.assertTrue(valid)

        self.assertTrue(form.use_dimple)
        self.assertFalse(form.use_fspipeline)
        self.assertFalse(form.run_aimless)

        self.assertEqual(form.pdb_model, 32)
        self.assertEqual(form.ref_space_group, "SGRP")
        self.assertEqual(form.custom_dimple, "ddimp")
        self.assertEqual(form.custom_fspipe, "")


class TestProjectFormSave(test.TestCase, ProjFormTesterMixin):
    def save_form(self, encrypted=False):
        """
        create project form and save it as pending project

        :return: created 'Project' database model object
        """
        request = self._request(encrypted=encrypted)

        proj_form = forms.ProjectForm(request.POST, request.FILES)

        with mock.patch("os.path.isdir") as isdir:
            # mock isdir() to report that all directories exist
            isdir.return_value = True

            # validate form to populate 'clean_data' fields
            valid = proj_form.is_valid()
            self.assertTrue(valid)  # sanity check that form _is_ valid

            return proj_form.save()

    def test_save(self):
        """
        test saving project form, and check
        that the database was updated
        """
        proj = self.save_form()

        # check that database entry looks reasonable
        db_proj = Project.get(proj_id=proj.id)
        self.assertEqual(db_proj.protein, PROTEIN)
        self.assertEqual(db_proj.proposal, PROPOSAL)
        self.assertEqual(db_proj.library.name, LIBRARY)
        self.assertFalse(db_proj.encrypted)
        self.assertIsNone(db_proj.encryption_key)

    def test_save_encrypted(self):
        """
        test saving project form, with encryption enabled, and check
        that the database was updated
        """
        proj = self.save_form(encrypted=True)

        # check that database entry looks reasonable
        db_proj = Project.get(proj_id=proj.id)
        self.assertEqual(db_proj.protein, PROTEIN)
        self.assertEqual(db_proj.proposal, PROPOSAL)
        self.assertEqual(db_proj.library.name, LIBRARY)
        self.assertTrue(db_proj.encrypted)
        self.assertIsNotNone(db_proj.encryption_key)


class TestProjectForm(unittest.TestCase, ProjFormTesterMixin):
    def _assertValidationError(self, form, field, expected_error_regexp):
        self.assertFalse(form.is_valid())

        err = form.errors[field].data[0]
        self.assertRegex(err.message, expected_error_regexp)

    def test_valid(self):
        """
        test validating a valid form
        """
        request = self._request()
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        with mock.patch("os.path.isdir") as isdir:
            # mock isdir() to report that all directories exist
            isdir.return_value = True

            is_valid = proj_form.is_valid()

            self.assertTrue(is_valid)

            isdir.assert_has_calls(
                [
                    mock.call(path.join(SITE.RAW_DATA_DIR, PROPOSAL)),
                    mock.call(path.join(SITE.RAW_DATA_DIR, PROPOSAL, SHIFT_1)),
                    mock.call(
                        path.join(SITE.RAW_DATA_DIR, PROPOSAL, SHIFT_1, "raw", PROTEIN)
                    ),
                    mock.call(path.join(SITE.RAW_DATA_DIR, PROPOSAL, SHIFT_2)),
                    mock.call(
                        path.join(SITE.RAW_DATA_DIR, PROPOSAL, SHIFT_2, "raw", PROTEIN)
                    ),
                ]
            )

    def test_invalid_empty_subdirs_list(self):
        """
        test validating a valid form where subdirs list is empty
        """
        request = self._request(subdirs="")
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        is_valid = proj_form.is_valid()
        self.assertFalse(is_valid)

    def test_protein_invalid_exp(self):
        """
        check that invalid characters in protein acronym are caught
        """
        request = self._request(protein="../../fo")
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        self._assertValidationError(proj_form, "protein", "invalid characters,.*")

    def test_no_library_file(self):
        """
        test the case when no fragment library file is provided
        """
        request = self._request()

        with mock.patch("os.path.isdir") as isdir:
            # mock isdir() to report that all directories exist
            isdir.return_value = True

            proj_form = forms.ProjectForm(request.POST, {})

            self._assertValidationError(
                proj_form, "fragments_file", "please specify fragments definitions file"
            )

    def test_library_file_parse_err(self):
        """
        test the case when provided fragment library file have parse errors
        """
        request = self._request(fragmenst_file_data="NO_COMMAS")

        with mock.patch("os.path.isdir") as isdir:
            # mock isdir() to report that all directories exist
            isdir.return_value = True

            proj_form = forms.ProjectForm(request.POST, request.FILES)

            self._assertValidationError(
                proj_form, "fragments_file", "unexpected number of cells"
            )

    def test_proposal_invalid_exp(self):
        """
        check that invalid characters in proposal number are caught
        """
        request = self._request(root="kiwi")
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        self._assertValidationError(
            proj_form, "root", "invalid Proposal Number 'kiwi', should be 8 digits"
        )

    def test_shift_list_invalid_exp(self):
        """
        check that invalid characters one of the shifts in the shifts list are caught
        """
        request = self._request(subdirs=f"{SHIFT_1},moin")
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        self._assertValidationError(proj_form, "subdirs", "invalid shift 'moin',.*")

    def test_proposal_not_found(self):
        """
        test specifying non-existing proposal
        """
        request = self._request()
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        _isdir = is_dir_mock(projects.proposal_dir(PROPOSAL))
        with mock.patch("os.path.isdir", _isdir):
            self._assertValidationError(proj_form, "root", "proposal '.*' not found")

    def test_shift_not_found(self):
        """
        test specifying non-existing shift in the shifts list field
        """
        request = self._request()
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        _isdir = is_dir_mock(projects.shift_dir(PROPOSAL, SHIFT_2))
        with mock.patch("os.path.isdir", _isdir):
            self._assertValidationError(
                proj_form, "subdirs", f"shift '{SHIFT_2}' not found"
            )

    def test_protein_not_found(self):
        """
        test specifying protein acronym, for which no data directory exist
        """
        request = self._request()
        proj_form = forms.ProjectForm(request.POST, request.FILES)

        _isdir = is_dir_mock(projects.protein_dir(PROPOSAL, SHIFT_1, PROTEIN))
        with mock.patch("os.path.isdir", _isdir):
            self._assertValidationError(
                proj_form,
                "subdirs",
                "shift '00000001' have no data for protein 'MyProt'",
            )
