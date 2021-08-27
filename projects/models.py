import typing
from datetime import datetime
from pony.orm import PrimaryKey, Required, Optional, Set, composite_key, desc


def _define_entities(db):
    class Project(db.Entity):
        proposal = PrimaryKey(str)
        protein = Required(str)
        encrypted = Required(bool)
        encryption_key = Optional(bytes)
        # store hard-coded 'database schema version' value,
        # to aid future migrations to modified schemas
        db_schema_version = Required(str, default="0")

    class PDB(db.Entity):
        id = PrimaryKey(int, auto=True)
        filename = Required(str, unique=True)
        pdb_id = Optional(str)

    class Crystal(db.Entity):
        id = PrimaryKey(str)
        fragment_id = Required(str)

        datasets = Set(lambda: DataSet)  # type: ignore

        #
        # crystal's origin data, as tracked in the wet-lab
        #
        solvent_concentration = Required(str)
        solvent = Required(str)

    class DataSet(db.Entity):
        id = PrimaryKey(int, auto=True)

        # root directory of where raw and auto-processed
        # data files are store relative to project's proposal dir
        data_root_dir = Required(str)

        crystal = Required(Crystal)
        run = Required(int)
        # limit to unique combinations of crystal and run
        composite_key(crystal, run)

        # the detector type used to capture the dataset, e.g. PILATUS3 2M
        detector = Required(str)

        # resolution at the edge of images, in Ångström
        resolution = Required(float)

        # number of collected diffraction images
        images = Required(int)

        # data collection start and end times, in UTC time
        start_time = Required(datetime)
        end_time = Optional(datetime)

        # beam transmission
        transmission = Required(float)

        wavelength = Required(float)
        start_angle = Required(float)
        angle_increment = Required(float)
        exposure_time = Required(float)
        detector_distance = Required(float)
        xbeam = Optional(float)
        ybeam = Optional(float)
        flux = Required(float)
        beam_shape = Required(str)
        slit_gap_horizontal = Optional(float)
        slit_gap_vertical = Optional(float)
        beam_size_at_sample_x = Required(float)
        beam_size_at_sample_y = Required(float)

        # references records of this dataset processed with some tool
        result = Set(lambda: Result)  # type: ignore

        snapshots = Set(lambda: DataSetSnapshot)  # type: ignore

        @property
        def name(self):
            """
            symbolic name used when we need to store generated files related to
            this dataset, typically used as a directory name

            the format is '<crystal_id>_<run_number>'
            """
            return f"{self.crystal.id}_{self.run}"

        def get_result(self, tool: str, input=None):
            """
            entry of the processing results of this dataset with specified tool,
            return None if this dataset have not been processed with that tool
            """
            return self.result.select(tool=tool, input=input).first()

        def tool_results(self, tool: str):
            """
            get all processing outcome for a tool, for example
            for 'dimple', the could be multiple results for jobs
            using 'edna', 'xds', etc inputs
            """
            for result in self.result.select(tool=tool):
                yield result.result

        def tool_result(self, tool: str) -> typing.Optional[str]:
            """
            check outcome of the processing of this dataset with
            specified tool

            returns 'ok'/'error' if processed or None if the dataset
            have not been processed with the tool
            """
            processed_data = self.get_result(tool)
            if processed_data is None:
                return None

            return processed_data.result

        def processed_successfully(self, tool: str) -> bool:
            return self.tool_result(tool) == "ok"

    class DataSetSnapshot(db.Entity):
        """
        snapshots (photos) of the crystal, taken when collection the dataset
        """

        dataset = Required(DataSet)
        index = Required(int)
        PrimaryKey(dataset, index)

    class Result(db.Entity):
        """
        overall results of processing a dataset with some tool
        """

        dataset = Required(DataSet)
        outputs = Set(lambda: Result)
        # input processed data used, for example for refine tools
        input = Optional(lambda: Result)

        # TODO use Enum (needs type database converter?)
        result = Required(str)  # 'ok', 'error', 'pending'

        # TODO use Enum (needs type database converter?)
        tool = Required(str)  # 'autoproc', 'edna', etc

        # we support only one entry per dataset, tool and input combination,
        # as when we re-run a tool, it overwrites old results
        composite_key(dataset, tool, input)

        # dataset statistics reference, when processed with processing tool
        process_result = Optional(lambda: ProcessResult)  # type: ignore

        # structure refine statistics reference, when processed with refine tool
        refine_result = Optional(lambda: RefineResult)  # type: ignore

        # ligand fit statistics reference, when processed with ligand fitting tool
        ligfit_result = Optional(lambda: LigfitResult)  # type: ignore

    class ProcessResult(db.Entity):
        id = PrimaryKey(int, auto=True)
        result = Required(Result, unique=True)
        space_group = Required(str)
        unit_cell_a = Required(float)
        unit_cell_b = Required(float)
        unit_cell_c = Required(float)
        unit_cell_alpha = Required(float)
        unit_cell_beta = Required(float)
        unit_cell_gamma = Required(float)
        low_resolution_average = Required(float)
        high_resolution_average = Required(float)
        low_resolution_out = Required(float)
        high_resolution_out = Required(float)
        reflections = Required(int)
        unique_reflections = Required(int)
        multiplicity = Required(float)
        i_sig_average = Required(float)
        i_sig_out = Required(float)
        r_meas_average = Required(float)
        r_meas_out = Required(float)
        completeness_average = Required(float)
        completeness_out = Required(float)
        mosaicity = Required(float)
        isa = Optional(float)

    class RefineResult(db.Entity):
        id = PrimaryKey(int, auto=True)
        result = Required(Result, unique=True)
        space_group = Required(str)
        resolution = Required(float)
        r_work = Required(float)
        r_free = Required(float)
        rms_bonds = Required(float)
        rms_angles = Required(float)
        unit_cell_a = Required(float)
        unit_cell_b = Required(float)
        unit_cell_c = Required(float)
        unit_cell_alpha = Required(float)
        unit_cell_beta = Required(float)
        unit_cell_gamma = Required(float)

        # blobs stored as JSON encoded list of coordinates
        blobs = Required(str)

        @property
        def process_tool(self) -> str:
            return self.result.input.tool

        @property
        def refine_tool(self) -> str:
            return self.result.tool

        @property
        def dataset(self):
            return self.result.dataset

        @property
        def name(self) -> str:
            """
            symbolic name, used when presenting a short name for this refine
            result to the user
            """
            # Note: this must be 'one line return' statment, as it's used in select()
            return f"{self.dataset.name}_{self.process_tool}_{self.refine_tool}"

        @property
        def isa(self):
            # look-up ISa value from processing result entry
            return self.result.input.process_result.isa

        def get_ligfit_result(self, ligfit_tool: str):
            ligfit_processed = self.dataset.result.select(
                tool=ligfit_tool, input=self.result
            ).first()

            if ligfit_processed is None:
                return None

            return ligfit_processed.ligfit_result

        #
        # previous() and next() methods allows to iterate over all refine
        # result entries in order by 'name'. The name is composed of dataset 'name'
        # and tools used to compute the refine result.
        #
        def previous(self):
            return (
                RefineResult.select(lambda r: r.name < self.name)
                .order_by(lambda r: desc(r.name))
                .first()
            )

        def next(self):
            return (
                RefineResult.select(lambda r: r.name > self.name)
                .order_by(lambda r: r.name)
                .first()
            )

    class LigfitResult(db.Entity):
        id = PrimaryKey(int, auto=True)
        result = Required(Result, unique=True)
        score = Required(float)
        # blobs, if available, stored as JSON encoded list of coordinates
        # NOTE: currenty ligfit tool derived blobs are not used anywhere in the application
        blobs = Optional(str)
