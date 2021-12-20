from django.forms import (
    Form,
    CharField,
    BooleanField,
    IntegerField,
    FileField,
    ValidationError,
)
from fragview.space_groups import get_space_group
from fragview.crystals import parse_crystals_csv, InvalidCrystalsCSV, Crystals


class _GetFieldMixin:
    def _get_field(self, name):
        return self.cleaned_data[name]


class _ProcJobForm(Form, _GetFieldMixin):
    spaceGroup = CharField(required=False)
    datasetsFilter = CharField(required=False)

    def clean_spaceGroup(self):
        space_group_name = self.space_group
        if space_group_name == "":
            # no space group specified, aka 'auto' space group
            return None

        space_group = get_space_group(space_group_name)
        if space_group is None:
            raise ValidationError(
                f"unsupported space group '{space_group_name}' specified"
            )

        return space_group

    # note: this properties are only valid after call to is_valid()

    @property
    def space_group(self):
        return self._get_field("spaceGroup")

    @property
    def datasets_filter(self):
        return self._get_field("datasetsFilter")


class LigfitForm(_ProcJobForm):
    useRhoFit = BooleanField(required=False)
    usePhenixLigfit = BooleanField(required=False)
    customLigFit = CharField(required=False)
    customRhoFit = CharField(required=False)
    cifMethod = CharField(required=False)

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

    @property
    def cif_method(self):
        return self._get_field("cifMethod")


class ProcessForm(_ProcJobForm):
    useDials = BooleanField(required=False)
    useXds = BooleanField(required=False)
    useXdsapp = BooleanField(required=False)
    useAutoproc = BooleanField(required=False)
    cellParams = CharField(required=False)
    friedelLaw = CharField(required=False)
    customXds = CharField(required=False)
    customAutoProc = CharField(required=False)
    customDials = CharField(required=False)
    customXdsApp = CharField(required=False)

    #
    # note: this properties are only valid after call to is_valid()
    #

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
    def custom_dimple(self):
        return self._get_field("customDimple")

    @property
    def custom_fspipe(self):
        return self._get_field("customFspipe")

    @property
    def run_aimless(self):
        return self._get_field("runAimless")

    def clean(self):
        if self.run_aimless and self.space_group is None:
            # if 'run aimless' enabled the space group must be specified
            raise ValidationError(
                dict(spaceGroup="space group required when aimless is enabled")
            )


class KillJobForm(Form):
    job_ids = CharField(required=False)

    def clean_job_ids(self):
        return self.cleaned_data["job_ids"].split(",")

    def get_job_ids(self):
        return self.cleaned_data["job_ids"]


class _CrystalsCsvForm(Form):
    crystals_csv_file = FileField()

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


class ProjectForm(_CrystalsCsvForm):
    protein = CharField()
    proposal = CharField()
    autoproc = BooleanField(required=False)
    encrypted = BooleanField(required=False)

    def get_values(self):
        cdata = self.cleaned_data

        return (
            cdata["protein"],
            cdata["proposal"],
            cdata["crystals_csv_file"],
            cdata["autoproc"],
            cdata["encrypted"],
        )


class CrystalsImportForm(_CrystalsCsvForm):
    def get_crystals(self) -> Crystals:
        return self.cleaned_data["crystals_csv_file"]
