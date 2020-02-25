from os import path
import unittest
from unittest import mock
from django import test
from django.test.client import RequestFactory
from fragview import forms
from django.conf import settings
from fragview import projects
from fragview.models import PendingProject


PROPOSAL = "12345678"
PROTEIN = "MyProt"
SHIFT = "00000000"
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


class FormTesterMixin:
    """
    Utility Mixin for testing Project Form class
    """
    ReqsFactory = RequestFactory()

    def _request(self,
                 protein=PROTEIN,
                 library="JBS",
                 proposal=PROPOSAL,
                 shift=SHIFT,
                 shift_list=f"{SHIFT_1},{SHIFT_2}"):

        return self.ReqsFactory.post(
            "/",  # we don't really care about the URL here
            dict(protein=protein,
                 library=library,
                 proposal=proposal,
                 shift=shift,
                 shift_list=shift_list))


class TestProjectFormSave(test.TestCase, FormTesterMixin):
    def save_form(self):
        """
        create project form as save it as pending project

        :return: created 'Project' database model object
        """
        request = self._request()

        proj_form = forms.ProjectForm(request.POST)
        with mock.patch("os.path.isdir") as isdir:
            # mock isdir() to report that all directories exist
            isdir.return_value = True

            proj_form.save_as_pending()

        return proj_form.instance

    def test_save(self):
        """
        test saving form as pending project, and check
        it's pending status in the database
        :return:
        """
        proj = self.save_form()

        # save project should be in pending state
        pend_proj = PendingProject.objects.get(project=proj.id)
        self.assertIsNotNone(pend_proj)

    def test_set_ready(self):
        """
        test setting project 'ready' and check it's pending
        state is droped from the database
        """
        proj = self.save_form()

        proj.set_ready()

        pend_proj = PendingProject.objects.filter(project=1)
        self.assertFalse(pend_proj.exists())


class TestProjectForm(unittest.TestCase, FormTesterMixin):

    def _assertValidationError(self, form, field, expected_error_regexp):
        self.assertFalse(form.is_valid())

        err = form.errors[field].data[0]
        self.assertRegex(err.message, expected_error_regexp)

    def test_valid(self):
        """
        test validating a valid form
        """
        request = self._request()

        proj_form = forms.ProjectForm(request.POST)

        with mock.patch("os.path.isdir") as isdir:
            # mock isdir() to report that all directories exist
            isdir.return_value = True

            is_valid = proj_form.is_valid()

            self.assertTrue(is_valid)

            isdir.assert_has_calls([
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL)),
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL, SHIFT)),
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL, SHIFT, "raw", PROTEIN)),
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL, SHIFT_1)),
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL, SHIFT_2)),
            ])

    def test_valid_empty_shift_list(self):
        """
        test validating a valid form wher shift list is empty
        """
        request = self._request(shift_list="")

        proj_form = forms.ProjectForm(request.POST)

        with mock.patch("os.path.isdir") as isdir:
            # mock isdir() to report that all directories exist
            isdir.return_value = True

            is_valid = proj_form.is_valid()

            self.assertTrue(is_valid)

            isdir.assert_has_calls([
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL)),
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL, SHIFT)),
                mock.call(path.join(settings.PROPOSALS_DIR, PROPOSAL, SHIFT, "raw", PROTEIN)),
            ])

    def test_protein_invalid_exp(self):
        """
        check that invalid characters in protein acronym are caught
        """
        request = self._request(protein="../../fo")
        proj_form = forms.ProjectForm(request.POST)

        self._assertValidationError(proj_form, "protein", "invalid characters,.*")

    def test_proposal_invalid_exp(self):
        """
        check that invalid characters in proposal number are caught
        """
        request = self._request(proposal="kiwi")
        proj_form = forms.ProjectForm(request.POST)

        self._assertValidationError(proj_form, "proposal", "invalid proposal 'kiwi',.*")

    def test_shift_invalid_exp(self):
        """
        check that invalid characters in shift number are caught
        """
        request = self._request(shift="orange")
        proj_form = forms.ProjectForm(request.POST)

        self._assertValidationError(proj_form, "shift", "invalid shift 'orange',.*")

    def test_shift_list_invalid_exp(self):
        """
        check that invalid characters one of the shifts in the shifts list are caught
        """
        request = self._request(shift_list=f"{SHIFT_1},moin")
        proj_form = forms.ProjectForm(request.POST)

        self._assertValidationError(proj_form, "shift_list", "invalid shift 'moin',.*")

    def test_proposal_not_found(self):
        """
        test specifying non-existing proposal
        """
        proj_form = forms.ProjectForm(self._request().POST)

        _isdir = is_dir_mock(projects.proposal_dir(PROPOSAL))
        with mock.patch("os.path.isdir", _isdir):
            self._assertValidationError(proj_form, "proposal", "proposal '.*' not found")

    def test_shift_not_found(self):
        """
        test specifying non-existing shift
        """
        proj_form = forms.ProjectForm(self._request().POST)

        _isdir = is_dir_mock(projects.shift_dir(PROPOSAL, SHIFT))
        with mock.patch("os.path.isdir", _isdir):
            self._assertValidationError(proj_form, "shift", "shift '.*' not found")

    def test_shifts_list_not_found(self):
        """
        test specifying non-existing shift in the shifts list field
        """
        proj_form = forms.ProjectForm(self._request().POST)

        _isdir = is_dir_mock(projects.shift_dir(PROPOSAL, SHIFT_2))
        with mock.patch("os.path.isdir", _isdir):
            self._assertValidationError(proj_form, "shift_list", f"shift '{SHIFT_2}' not found")

    def test_protein_not_found(self):
        """
        test specifying protein acronym, for which no data directory exist
        """
        proj_form = forms.ProjectForm(self._request().POST)

        _isdir = is_dir_mock(projects.protein_dir(PROPOSAL, SHIFT, PROTEIN))
        with mock.patch("os.path.isdir", _isdir):
            self._assertValidationError(proj_form, "protein", f"data for protein '.*' not found")
