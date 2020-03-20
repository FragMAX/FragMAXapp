import re
from os import path
from django import forms
from fragview import projects, fraglib, encryption
from .models import Project, PendingProject, EncryptionKey


def _is_8_digits(str, subject="shift"):
    if re.match("^\\d{8}$", str) is None:
        raise forms.ValidationError(f"invalid {subject} '{str}', should be 8 digits")

    return str


class ProjectForm(forms.Form):
    model = None

    protein = forms.CharField()
    # library name and fragment file are required for new projects,
    # but not when modifying existing projects
    library_name = forms.CharField(required=False)
    fragments_file = forms.FileField(required=False)
    proposal = forms.CharField()
    shift = forms.CharField()
    shift_list = forms.CharField(required=False)
    # set required=False for this field, as it's not always submitted when unchecked
    encrypted = forms.BooleanField(required=False)

    def __init__(self, data, files, model=None):
        self.model = model
        if data is None and model is not None:
            data = dict(
                protein=model.protein,
                library_name=model.library.name,
                proposal=model.proposal,
                shift=model.shift,
                shift_list=model.shift_list,
                encrypted=model.encrypted)

        super().__init__(data, files)

    #
    # first each individual field is validated on 'syntactic' level,
    # i.e. we check that they match specific regexp
    #
    # we are overlay strict with all the field's contents, as they are used to build
    # paths, so we don't allow any funny characters, to avoid potential path hacks
    #

    def _check_alphanumeric(self, field_name):
        field_val = self.cleaned_data[field_name]

        if re.match("^\\w+$", field_val) is None:
            raise forms.ValidationError("invalid characters, use numbers and letters")

        return field_val

    def clean_protein(self):
        return self._check_alphanumeric("protein")

    def clean_library_name(self):
        if self.model:
            # at the moment, the library name can't be modified
            # for existing project, don't do any validation
            return

        return self._check_alphanumeric("library_name")

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

    def _validate_library(self):
        # make sure fragments specification file was provided
        frags_file = self.files.get("fragments_file")
        if frags_file is None:
            if self.model is None:
                return dict(fragments_file="please specify fragments definitions file")
            return {}

        # check if fragments file is valid by parsing it
        try:
            self.cleaned_data["fragments"] = fraglib.parse_uploaded_file(frags_file)
        except fraglib.FraglibError as e:
            # failed to parse fragments file, propagate parse error to the user
            return dict(fragments_file=e.error_message())

        return {}

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

    #
    # as a second step, perform 'semantic' validation, e.g. check
    # that all directories for specified proposal, protein, etc
    # actually exist
    #

    def _is_encrypted(self):
        """
        returns true if form's 'encrypted' checkbox was checked
        """
        if "encrypted" not in self.cleaned_data:
            # handle the cases when value is not submitted by the browser
            # when 'encrypted' checkbox is unchecked
            return False

        return self.cleaned_data["encrypted"]

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

        library_errors = self._validate_library()
        errors.update(library_errors)

        if len(errors) > 0:
            # there were errors
            raise forms.ValidationError(errors)

    def update(self):
        assert self.model is not None

        self.model.protein = self.cleaned_data["protein"]
        self.model.proposal = self.cleaned_data["proposal"]
        self.model.shift = self.cleaned_data["shift"]
        self.model.shift_list = self.cleaned_data["shift_list"]

        self.model.save()

    def save(self, pending=True):
        # save the library
        library = fraglib.save_new_library(
            self.cleaned_data["library_name"], self.cleaned_data["fragments"])

        # save the 'Project' model to DB
        encrypted = self._is_encrypted()
        args = dict(
            protein=self.cleaned_data["protein"],
            library=library,
            proposal=self.cleaned_data["proposal"],
            shift=self.cleaned_data["shift"],
            encrypted=encrypted)

        # check if there is any shift_list specified
        shift_list = self.cleaned_data["shift_list"]
        if len(shift_list) > 0:
            args["shift_list"] = shift_list

        proj = Project(**args)
        proj.save()

        if encrypted:
            # encrypted mode enabled, generate encryption key
            key = EncryptionKey(key=encryption.generate_key(),
                                project=proj)
            key.save()

        # add 'pending' entry, if requested
        if pending:
            PendingProject(project=proj).save()

        return proj
