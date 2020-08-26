from pathlib import Path
from fragview.projects import project_results_dir, project_datasets, project_shift_dirs
from fragview.fileio import subdirs
from fragview.dsets import get_datasets


def _dsets_with_tool_status(proj, tools, status):
    """
    get all datasets with specified tool processing status
    """
    for dset in get_datasets(proj):
        for tool in tools:
            tool_stat = getattr(dset.status, tool)
            if tool_stat == status:
                yield f"{dset.image_prefix}_{dset.run}"
                # handle the cases where request status matches multiple tools,
                # skip the test of the tools statuses
                break


def get_proc_datasets(proj, filter):
    """
    perform datasets filtering for 'data processing' jobs

    filters supported:

    'ALL' - all of the project's datasets

    'NEW' - datasets that have not been processes yet,
            that is, datasets that don't have a 'results' dir

    otherwise the filter is expected to be a comma separated list of dataset names
    """

    def _new_datasets():
        results_dir = project_results_dir(proj)
        for dset in project_datasets(proj):
            if Path(results_dir, dset).is_dir():
                continue

            yield dset

    def _selected_datasets():
        for dset in filter.split(","):
            yield dset

    if filter == "ALL":
        return project_datasets(proj)

    if filter == "NEW":
        return _new_datasets()

    return _selected_datasets()


def get_refine_datasets(proj, filter, use_fspipeline, use_dimple, use_buster):
    """
    perform datasets filtering for 'structure refinement' jobs

    filters supported:

    'ALL' - all of the project's datasets

    'NEW' - datasets that have not been processes with refinement tool yet

    otherwise the filter is expected to be a comma separated list of dataset names

    use_fspipeline, use_dimple and use_buster flags are used with 'NEW' filter, and
    specify the tools for which the processing status will be checked
    """

    def _new_datasets():
        def _get_tools():
            # at least one tool must be used
            assert use_fspipeline or use_dimple or use_buster

            tools = []

            if use_fspipeline:
                tools.append("fspipeline")

            if use_dimple:
                tools.append("dimple")

            if use_buster:
                tools.append("buster")

            return tools

        return _dsets_with_tool_status(proj, _get_tools(), "unknown")

    def _selected_datasets():
        for dset in filter.split(","):
            yield dset

    if filter == "ALL":
        return project_datasets(proj)

    if filter == "NEW":
        return _new_datasets()

    return _selected_datasets()


def get_ligfit_datasets(proj, filter, use_ligand_fit, use_rho_fit):
    """
    perform datasets filtering for 'ligand fitting' jobs

    filters supported:

    'ALL' - all of the project's datasets

    'NEW' - datasets that have not been processes with ligand fitting tools yet

    otherwise the filter is expected to be a comma separated list of dataset names

    use_ligand_fit and use_rho_fit flags are used with 'NEW' filter, and specify
    the tools for which the processing status will be checked
    """

    def _exclude_apo(dsets):
        for dset in dsets:
            if "apo" in dset.lower():
                continue
            yield dset

    def _new_datasets():
        def _get_tools():
            # at least one tool must be used
            assert use_ligand_fit or use_rho_fit

            tools = []

            if use_ligand_fit:
                tools.append("ligand_fit")

            if use_rho_fit:
                tools.append("rho_fit")

            return tools

        return _dsets_with_tool_status(proj, _get_tools(), "unknown")

    def _selected_datasets():
        for dset in filter.split(","):
            yield dset

    if filter == "ALL":
        datasets = project_datasets(proj)
    elif filter == "NEW":
        datasets = _new_datasets()
    else:
        datasets = _selected_datasets()

    return _exclude_apo(datasets)


def get_ligfit_pdbs(proj, datasets):
    """
    get all 'final' PDBs for specified datasets

    for filter syntax, see get_ligfit_datasets() documentation
    """
    results_dir = project_results_dir(proj)

    for dset in datasets:
        dset_res_dir = Path(results_dir, dset)
        for sdir in subdirs(dset_res_dir, 2):
            pdb_path = Path(sdir, "final.pdb")
            if pdb_path.is_file():
                yield str(pdb_path)


def _get_dataset_xml_file(proj, data_set):
    xml_glob_exp = Path(
        f"xds_{data_set}_*",
        "fastdp",
        "cn*",
        "ISPyBRetrieveDataCollectionv1_4",
        "ISPyBRetrieveDataCollectionv1_4_dataOutput.xml",
    )

    set_name, run = data_set.rsplit("_", 2)

    for shift_dir in project_shift_dirs(proj):
        set_dir = Path(shift_dir, "process", proj.protein, set_name)

        if not set_dir.is_dir():
            continue

        xml_files = list(set_dir.glob(str(xml_glob_exp)))
        if len(xml_files) > 0:
            return xml_files[0]


def get_xml_files(proj, datasets):
    """
    filter datasets according to specified filter and for all matching
    datasets, return dataset's metadata XML

    for filter syntax, see get_proc_datasets() documentation
    """

    for dset in datasets:
        yield _get_dataset_xml_file(proj, dset)
