from os import path
from django import forms
from . import projects
from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ("protein", "library", "proposal", "shift", "shift_list")

    def _validate_shift_list(self, proposal):
        shift_list = self.cleaned_data["shift_list"]

        for shift in shift_list.split(","):
            if not path.isdir(projects.shift_dir(proposal, shift)):
                # bail on first incorrect shift ID
                return dict(shift_list=f"shift '{shift}' not found")

        # all shifts looks good, no errors
        return {}

    def clean(self):
        # TODO: we should not allow wierd characters in all these fields
        # TODO: before we construct paths, otherwise it a potentional security issue?

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
