import re
from os import path
from django import forms
from . import projects
from .models import Project


def _is_8_digits(str, subject="shift"):
    if re.match("^\\d{8}$", str) is None:
        raise forms.ValidationError(f"invalid {subject} '{str}', should be 8 digits")

    return str


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("protein", "library", "proposal", "shift", "shift_list")

    #
    # first each individual field is validated on 'syntactic' level,
    # i.e. we check that they match specific regexp
    #
    # we are overlay strict with all the field's contents, as they are used to build
    # paths, so we don't allow any funny characters, to avoid potential path hacks
    #

    def clean_protein(self):
        protein = self.cleaned_data["protein"]

        if re.match("^\\w+$", protein) is None:
            raise forms.ValidationError("invalid characters, use numbers and letters")

        return protein

    def clean_proposal(self):
        return _is_8_digits(self.cleaned_data["proposal"], "proposal")

    def clean_shift(self):
        return _is_8_digits(self.cleaned_data["shift"])

    def clean_shift_list(self):
        shift_list = self.cleaned_data["shift_list"].strip()

        if not shift_list:
            # empty shift list is valid
            return shift_list

        for shift in shift_list.split(","):
            _is_8_digits(shift)

        return shift_list

    #
    # as a second step, perform 'semantic' validation, e.g. check
    # that all directories for specified proposal, protein, etc
    # actually exist
    #

    def _validate_shift_list(self, proposal):
        shift_list = self.cleaned_data["shift_list"].strip()

        if not shift_list:
            # empty shift list, no need validate anything more
            return {}

        for shift in shift_list.split(","):
            if not path.isdir(projects.shift_dir(proposal, shift)):
                # bail on first incorrect shift ID
                return dict(shift_list=f"shift '{shift}' not found")

        # all shifts looks good, no errors
        return {}

    def clean(self):
        if self.errors:
            # there were error(s) during the regexp validation,
            # we can't do the 'semantic' validation
            return

        errors = dict()

        # check that proposal directory exists
        proposal = self.cleaned_data["proposal"]
        if not path.isdir(projects.proposal_dir(proposal)):
            # if the proposal is wrong, we can't validate other fields
            # just tell the user that proposal is wrong
            raise forms.ValidationError(
                dict(proposal=f"proposal '{proposal}' not found"))

        # check that shift directory exists
        shift = self.cleaned_data["shift"]
        if not path.isdir(projects.shift_dir(proposal, shift)):
            errors["shift"] = f"shift '{shift}' not found"
        else:  # only validate protein dir, if the shift dir is good
            protein = self.cleaned_data["protein"]
            if not path.isdir(projects.protein_dir(proposal, shift, protein)):
                errors["protein"] = f"data for protein '{protein}' not found"

        shift_list_errors = self._validate_shift_list(proposal)
        errors.update(shift_list_errors)

        if len(errors) > 0:
            # there were errors
            raise forms.ValidationError(errors)
