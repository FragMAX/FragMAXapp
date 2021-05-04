from typing import Optional
from fragview.projects import Project


def _no_results_datasets(project: Project, tool: str):
    for dataset in project.get_datasets():
        res = dataset.result.select(tool=tool).first()
        if res is None:
            yield dataset


def _dataset_by_ids(project: Project, dataset_ids: str):
    for dset_id in dataset_ids.split(","):
        yield project.get_dataset(dset_id)


def get_proc_datasets(project: Project, filter: str, tool: str):
    """
    perform datasets filtering for 'data processing' jobs

    filters supported:

    'ALL' - all of the project's datasets

    'NEW' - datasets that have not been processes yet with specified tool

    otherwise the filter is expected to be a comma separated list of dataset IDs
    """
    if filter == "ALL":
        return project.get_datasets()

    if filter == "NEW":
        return _no_results_datasets(project, tool)

    return _dataset_by_ids(project, filter)


def get_refine_datasets(project: Project, filter: str, refine_tool: str):
    """
    perform datasets filtering for 'structure refinement' jobs

    filters supported:

    'ALL' - all of the project's datasets

    'NEW' - datasets that have not been processes with specified refinement tool yet

    otherwise the filter is expected to be a comma separated list of dataset names
    """
    if filter == "ALL":
        return project.get_datasets()

    if filter == "NEW":
        return _no_results_datasets(project, refine_tool)

    return _dataset_by_ids(project, filter)


def get_ligfit_datasets(project: Project, filter: str, ligfit_tool: Optional[str]):
    """
    perform datasets filtering for 'ligand fitting' jobs

    filters supported:

    'ALL' - all of the project's datasets

    'NEW' - datasets that have not been processes with specified ligand fitting tools yet

    otherwise the filter is expected to be a comma separated list of dataset names
    """
    if filter == "ALL":
        return project.get_datasets()

    if filter == "NEW":
        assert ligfit_tool is not None
        return _no_results_datasets(project, ligfit_tool)

    return _dataset_by_ids(project, filter)
