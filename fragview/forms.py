import re
from os import path
from django import forms
from fragview import projects, fraglib, encryption
from fragview.models import Project, EncryptionKey
from fragview.sites import SITE
from fragview.sites.plugin import ProjectLayout


class _ProcJobForm(forms.Form):
    datasetsFilter = forms.CharField(required=False)
    hpcNodes = forms.IntegerField()
    cifMethod = forms.CharField(required=False)

    def _get_field(self, name):
        return self.cleaned_data[name]

    # note: this properties are only valid after call to is_valid()

    @property
    def datasets_filter(self):
        return self._get_field("datasetsFilter")

    @property
    def hpc_nodes(self):
        return self._get_field("hpcNodes")

    @property
    def cif_method(self):
        return self._get_field("cifMethod")


class LigfitForm(_ProcJobForm):
    useRhoFit = forms.BooleanField(required=False)
    usePhenixLigfit = forms.BooleanField(required=False)

    @property
    def use_rho_fit(self):
        return self._get_field("useRhoFit")

    @property
    def use_phenix_ligfit(self):
        return self._get_field("usePhenixLigfit")


class ProcessForm(_ProcJobForm):
    useDials = forms.BooleanField(required=False)
    useXdsxscale = forms.BooleanField(required=False)
    useXdsapp = forms.BooleanField(required=False)
    useAutoproc = forms.BooleanField(required=False)
    spaceGroup = forms.CharField(required=False)
    cellParams = forms.CharField(required=False)
    friedelLaw = forms.CharField(required=False)
    customXds = forms.CharField(required=False)
    customAutoProc = forms.CharField(required=False)
    customDials = forms.CharField(required=False)
    customXdsApp = forms.CharField(required=False)

    # note: this properties are only valid after call to is_valid()

    @property
    def use_dials(self):
        return self._get_field("useDials")

    @property
    def use_xdsxscale(self):
        return self._get_field("useXdsxscale")

    @property
    def use_xdsapp(self):
        return self._get_field("useXdsapp")

    @property
    def use_autoproc(self):
        return self._get_field("useAutoproc")

    @property
    def space_group(self):
        return self._get_field("spaceGroup")

    @property
    def cell_params(self):
        return self._get_field("cellParams")

    @property
    def friedel_law(self):
        return self._get_field("friedelLaw")

    @property
    def custom_xds(self):
        return self._get_field("customXds")

    @property
    def custom_autoproc(self):
        return self._get_field("customAutoProc")

    @property
    def custom_dials(self):
        return self._get_field("customDials")

    @property
    def custom_xdsapp(self):
        return self._get_field("customXdsApp")


class RefineForm(_ProcJobForm):
    useDimple = forms.BooleanField(required=False)
    useBuster = forms.BooleanField(required=False)
    useFSpipeline = forms.BooleanField(required=False)
    refSpaceGroup = forms.CharField(required=False)
    customRefDimple = forms.CharField(required=False)
    customRefBuster = forms.CharField(required=False)
    customRefFspipe = forms.CharField(required=False)
    runAimless = forms.BooleanField(required=False)

    # PDB model field is a drop-down, but we treat it as integer, as
    # we don't want to bother with validating the provided model ID
    pdbModel = forms.IntegerField()

    # note: this properties are only valid after call to is_valid()

    @property
    def use_dimple(self):
        return self._get_field("useDimple")

    @property
    def use_buster(self):
        return self._get_field("useBuster")

    @property
    def use_fspipeline(self):
        return self._get_field("useFSpipeline")

    @property
    def pdb_model(self):
        return self._get_field("pdbModel")

    @property
    def ref_space_group(self):
        return self._get_field("refSpaceGroup")

    @property
    def custom_dimple(self):
        return self._get_field("customRefDimple")

    @property
    def custom_buster(self):
        return self._get_field("customRefBuster")

    @property
    def custom_fspipe(self):
        return self._get_field("customRefFspipe")

    @property
    def run_aimless(self):
        return self._get_field("runAimless")

    def clean(self):
        if self.run_aimless and self.ref_space_group == "":
            # if 'run aimless' enabled the space group must be specified
            raise forms.ValidationError(
                dict(refSpaceGroup="space group required when aimless is enabled"))


class ProjectForm(forms.Form):
    model = None

    protein = forms.CharField()
    # library name and fragment file are required for new projects,
    # but not when modifying existing projects
    library_name = forms.CharField(required=False)
    fragments_file = forms.FileField(required=False)
    root = forms.CharField()
    subdirs = forms.CharField(required=False)
    # set required=False for this field, as it's not always submitted when unchecked
    encrypted = forms.BooleanField(required=False)

    def __init__(self, data, files, model=None):
        self.proj_layout = SITE.get_project_layout()
        self.model = model
        if data is None and model is not None:
            data = dict(
                protein=model.protein,
                library_name=model.library.name,
                root=model.proposal,
                subdirs=model.shift_list,
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

    def clean_root(self):
        root = self.cleaned_data["root"].strip()

        try:
            self.proj_layout.check_root(root)
        except ProjectLayout.ValidationError as e:
            raise forms.ValidationError(str(e))

        return root

    def clean_subdirs(self):
        subdirs = self.cleaned_data["subdirs"].strip()

        try:
            self.proj_layout.check_subdirs(subdirs)
        except ProjectLayout.ValidationError as e:
            raise forms.ValidationError(str(e))

        return subdirs

    def clean_library_name(self):
        if self.model:
            # at the moment, the library name can't be modified
            # for existing project, don't do any validation
            return

        return self._check_alphanumeric("library_name")

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

    def _validate_root(self, root, protein):
        if not path.isdir(projects.protein_dir(root, '', protein)):
            return dict(root=f"proposal '{root}' have no data for protein '{protein}'")

        # root directory looks good
        return {}

    def _validate_subdirs(self, root, protein):
        subdirs = self.cleaned_data["subdirs"].strip()

        shifts = subdirs.split(",")
        for shift in shifts:
            if not path.isdir(projects.shift_dir(root, shift)):
                # bail on first incorrect shift ID
                return dict(subdirs=f"shift '{shift}' not found")

            # check that this shift dir have the protein directory
            if not path.isdir(projects.protein_dir(root, shift, protein)):
                return dict(subdirs=f"shift '{shift}' have no data for protein '{protein}'")

        if self.model is not None:
            # while updating existing project, prevent user from removing the 'main' shift
            main_shift = self.model.shift
            if main_shift not in shifts:
                return dict(subdirs=f"can't remove main shift '{main_shift}'")

        # all shifts looks good, no errors
        return {}

    #
    # as a second step, perform 'semantic' validation, e.g. check
    # that all directories for specified proposal, protein, etc
    # actually exist
    #

    def clean(self):
        if self.errors:
            # there were error(s) during the regexp validation,
            # we can't do the 'semantic' validation
            return

        errors = dict()

        # check that root directory exists
        root = self.cleaned_data["root"]
        protein = self.cleaned_data["protein"]

        if not path.isdir(projects.proposal_dir(root)):
            # if the proposal is wrong, we can't validate other fields
            # just tell the user that proposal is wrong
            raise forms.ValidationError(
                dict(root=f"proposal '{root}' not found"))

        if self.proj_layout.subdirs() is None:
            # for plain data layout, check that root folder have the protein
            root_errors = self._validate_root(root, protein)
            errors.update(root_errors)
        else:
            # for shifts data layout, check that all subdirs have proteins
            subdirs_errors = self._validate_subdirs(root, protein)
            errors.update(subdirs_errors)

        library_errors = self._validate_library()
        errors.update(library_errors)

        if len(errors) > 0:
            # there were errors
            raise forms.ValidationError(errors)

    def update(self):
        assert self.model is not None

        self.model.protein = self.cleaned_data["protein"]
        self.model.proposal = self.cleaned_data["root"]
        self.model.shift_list = self.cleaned_data["subdirs"]

        self.model.save()

    def save(self):
        # save the library
        library = fraglib.save_new_library(
            self.cleaned_data["library_name"], self.cleaned_data["fragments"])

        #
        # save the 'Project' model to DB
        #

        encrypted = self.cleaned_data["encrypted"]
        subdirs = self.cleaned_data["subdirs"]
        # pick first specified shift as 'main' shift
        shift = subdirs.split(",")[0]

        proj = Project(
            protein=self.cleaned_data["protein"],
            library=library,
            proposal=self.cleaned_data["root"],
            shift=shift,
            shift_list=subdirs,
            encrypted=encrypted)
        proj.save()

        if encrypted:
            # encrypted mode enabled, generate encryption key
            key = EncryptionKey(key=encryption.generate_key(),
                                project=proj)
            key.save()

        return proj


class NewLibraryForm(forms.Form):
    model = None

    fragments_file = forms.FileField(required=False)
