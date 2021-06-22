from django.forms import (
    Form,
    CharField,
    BooleanField,
    IntegerField,
    FileField,
    ValidationError,
)
from fragview.crystals import parse_crystals_csv, InvalidCrystalsCSV


class _GetFieldMixin:
    def _get_field(self, name):
        return self.cleaned_data[name]


class _ProcJobForm(Form, _GetFieldMixin):
    datasetsFilter = CharField(required=False)
    cifMethod = CharField(required=False)

    # note: this properties are only valid after call to is_valid()

    @property
    def datasets_filter(self):
        return self._get_field("datasetsFilter")

    @property
    def cif_method(self):
        return self._get_field("cifMethod")


class LigfitForm(_ProcJobForm):
    useRhoFit = BooleanField(required=False)
    usePhenixLigfit = BooleanField(required=False)
    customLigFit = CharField(required=False)
    customRhoFit = CharField(required=False)

    @property
    def use_rho_fit(self):
        return self._get_field("useRhoFit")

    @property
    def use_phenix_ligfit(self):
        return self._get_field("usePhenixLigfit")

    @property
    def custom_ligfit(self):
        return self._get_field("customLigFit")

    @property
    def custom_rhofit(self):
        return self._get_field("customRhoFit")


class ProcessForm(_ProcJobForm):
    useDials = BooleanField(required=False)
    useXds = BooleanField(required=False)
    useXdsapp = BooleanField(required=False)
    useAutoproc = BooleanField(required=False)
    spaceGroup = CharField(required=False)
    cellParams = CharField(required=False)
    friedelLaw = CharField(required=False)
    customXds = CharField(required=False)
    customAutoProc = CharField(required=False)
    customDials = CharField(required=False)
    customXdsApp = CharField(required=False)

    # note: this properties are only valid after call to is_valid()

    @property
    def use_dials(self):
        return self._get_field("useDials")

    @property
    def use_xds(self):
        return self._get_field("useXds")

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
    useDimple = BooleanField(required=False)
    useFSpipeline = BooleanField(required=False)
    refSpaceGroup = CharField(required=False)
    customDimple = CharField(required=False)
    customFspipe = CharField(required=False)
    runAimless = BooleanField(required=False)

    # PDB model field is a drop-down, but we treat it as integer, as
    # we don't want to bother with validating the provided model ID
    pdbModel = IntegerField()

    # note: this properties are only valid after call to is_valid()

    @property
    def use_dimple(self):
        return self._get_field("useDimple")

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
        return self._get_field("customDimple")

    @property
    def custom_fspipe(self):
        return self._get_field("customFspipe")

    @property
    def run_aimless(self):
        return self._get_field("runAimless")

    def clean(self):
        if self.run_aimless and self.ref_space_group == "":
            # if 'run aimless' enabled the space group must be specified
            raise ValidationError(
                dict(refSpaceGroup="space group required when aimless is enabled")
            )


class KillJobForm(Form):
    job_ids = CharField(required=False)

    def clean_job_ids(self):
        ids = self.cleaned_data["job_ids"].split(",")
        if len(ids) < 1:
            raise ValidationError("no job IDs specified")

        return ids

    def get_job_ids(self):
        return self.cleaned_data["job_ids"]


class ProjectForm(Form):
    crystals_csv_file = FileField()
    protein = CharField()
    proposal = CharField()
    autoproc = BooleanField(required=False)
    encrypted = BooleanField(required=False)

    def clean_crystals_csv_file(self):
        csv_file = self.cleaned_data["crystals_csv_file"]
        try:
            return parse_crystals_csv(csv_file)
        except InvalidCrystalsCSV as e:
            raise ValidationError(str(e))

    def get_error_message(self):
        csv_errors = self.errors.get("crystals_csv_file")
        if csv_errors:
            return f"Could not parse Crystals CSV.\n{csv_errors[0]}"

        assert False, "unexpected form error"

    def get_values(self):
        cdata = self.cleaned_data

        return (
            cdata["protein"],
            cdata["proposal"],
            cdata["crystals_csv_file"],
            cdata["autoproc"],
            cdata["encrypted"],
        )
