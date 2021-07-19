from fragview.scraper import (
    scrape_processing_results,
    scrape_refine_results,
    scrape_ligfit_results,
    ToolStatus,
    ProcStats,
    RefineResult,
    LigfitResult,
)
from fragview.projects import Project
from fragview.sites import SITE
from fragview.sites.plugin import Pipeline


AUTOPROC_TOOLS = {
    Pipeline.EDNA_PROC: "edna",
    Pipeline.AUTO_PROC: "autoproc",
}


def _supported_autoproc_tools():
    supported_tools = set()
    for pipeline in SITE.get_supported_pipelines():
        tool = AUTOPROC_TOOLS.get(pipeline)
        if tool is not None:
            supported_tools.add(tool)

    return supported_tools


# TODO remove me
def set_imported_autoproc_status(project):
    tools = _supported_autoproc_tools()

    if not tools:
        # this site does not support importing
        # any auto-processed data, nothing to do here
        return

    for dataset in get_datasets(project):
        dset_name = f"{dataset.image_prefix}_{dataset.run}"
        for tool in tools:
            print(f"scrape {dset_name} for {tool}")
            # TODO: re-structure code so we don't rewrite
            # TODO: allstatus.csv for each dataset/tool combination,
            # TODO: which is, ehhh, somewhat un-optimal
            update_proc_tool_status(project, tool, dset_name)


def _tool_status_to_result(status: ToolStatus) -> str:
    if status == ToolStatus.SUCCESS:
        return "ok"
    if status == ToolStatus.FAILURE:
        return "error"

    assert status == ToolStatus.UNKNOWN


def _update_result_entry(
    project: Project, dataset, tool, status: ToolStatus, input=None
):
    result = _tool_status_to_result(status)
    if result is None:
        # unknown status, don't add to database
        return

    result_entry = dataset.get_result(tool, input)

    if result_entry is None:
        # create new entry
        result_entry = project.db.Result(
            dataset=dataset, result=result, tool=tool, input=input
        )
    else:
        # update existing entry
        result_entry.result = result
        result_entry.input = input

    return result_entry


def update_proc_tool_status(project, tool, dataset):
    scraped_result = scrape_processing_results(project, tool, dataset)
    if scraped_result is None:
        # no results
        return

    print(f"{tool} {scraped_result.status}")

    result_entry = _update_result_entry(project, dataset, tool, scraped_result.status)
    if scraped_result.status == ToolStatus.SUCCESS:
        _update_proc_result_entry(project, result_entry, scraped_result)


def _update_proc_result_entry(project: Project, result_entry, result: ProcStats):
    proc_res = result_entry.process_result

    if proc_res is None:
        project.db.ProcessResult(
            result=result_entry,
            space_group=result.space_group,
            unit_cell_a=result.unit_cell_a,
            unit_cell_b=result.unit_cell_b,
            unit_cell_c=result.unit_cell_c,
            unit_cell_alpha=result.unit_cell_alpha,
            unit_cell_beta=result.unit_cell_beta,
            unit_cell_gamma=result.unit_cell_gamma,
            low_resolution_average=result.low_resolution_average,
            high_resolution_average=result.high_resolution_average,
            low_resolution_out=result.low_resolution_out,
            high_resolution_out=result.high_resolution_out,
            reflections=result.reflections,
            unique_reflections=result.unique_reflections,
            multiplicity=result.multiplicity,
            i_sig_average=result.i_sig_average,
            i_sig_out=result.i_sig_out,
            r_meas_average=result.r_meas_average,
            r_meas_out=result.r_meas_out,
            completeness_average=result.completeness_average,
            completeness_out=result.completeness_out,
            mosaicity=result.mosaicity,
            isa=result.isa,
        )
        return

    proc_res.space_group = result.space_group
    proc_res.unit_cell_a = result.unit_cell_a
    proc_res.unit_cell_b = result.unit_cell_b
    proc_res.unit_cell_c = result.unit_cell_c
    proc_res.unit_cell_alpha = result.unit_cell_alpha
    proc_res.unit_cell_beta = result.unit_cell_beta
    proc_res.unit_cell_gamma = result.unit_cell_gamma
    proc_res.low_resolution_average = result.low_resolution_average
    proc_res.high_resolution_average = result.high_resolution_average
    proc_res.low_resolution_out = result.low_resolution_out
    proc_res.high_resolution_out = result.high_resolution_out
    proc_res.reflections = result.reflections
    proc_res.unique_reflections = result.unique_reflections
    proc_res.multiplicity = result.multiplicity
    proc_res.i_sig_average = result.i_sig_average
    proc_res.i_sig_out = result.i_sig_out
    proc_res.r_meas_average = result.r_meas_average
    proc_res.r_meas_out = result.r_meas_out
    proc_res.completeness_average = result.completeness_average
    proc_res.completeness_out = result.completeness_out
    proc_res.mosaicity = result.mosaicity
    proc_res.isa = result.isa


def _update_refine_result_entry(
    project: Project, refine_tool_result, result: RefineResult
):
    if refine_tool_result.refine_result is None:
        # create new entry
        project.db.RefineResult(
            result=refine_tool_result,
            space_group=result.space_group,
            resolution=result.resolution,
            r_work=result.r_work,
            r_free=result.r_free,
            rms_bonds=result.rms_bonds,
            rms_angles=result.rms_angles,
            unit_cell_a=result.cell.a,
            unit_cell_b=result.cell.b,
            unit_cell_c=result.cell.c,
            unit_cell_alpha=result.cell.alpha,
            unit_cell_beta=result.cell.beta,
            unit_cell_gamma=result.cell.gamma,
            blobs=result.blobs,
        )
        return

    # update existing entry
    ref_res = refine_tool_result.refine_result
    ref_res.space_group = result.space_group
    ref_res.resolution = result.resolution
    ref_res.r_work = result.r_work
    ref_res.r_free = result.r_free
    ref_res.rms_bonds = result.rms_bonds
    ref_res.rms_angles = result.rms_angles
    ref_res.unit_cell_a = result.cell.a
    ref_res.unit_cell_b = result.cell.b
    ref_res.unit_cell_c = result.cell.c
    ref_res.unit_cell_alpha = result.cell.alpha
    ref_res.unit_cell_beta = result.cell.beta
    ref_res.unit_cell_gamma = result.cell.gamma
    ref_res.blobs = result.blobs


def _update_ligfit_result_entry(
    project: Project, ligfit_tool_result, result: LigfitResult
):
    if ligfit_tool_result.ligfit_result is None:
        # create new entry
        args = dict(result=ligfit_tool_result, score=result.score)
        if result.blobs is not None:
            args["blobs"] = result.blobs
        project.db.LigfitResult(**args)
        return

    # update existing entry
    ligfit_res = ligfit_tool_result.ligfit_result
    ligfit_res.score = result.score
    if result.blobs is not None:
        ligfit_res.blobs = result.blobs


def update_refine_tool_status(project: Project, tool: str, dataset):
    for result in scrape_refine_results(project, tool, dataset):
        proc_tool_entry = dataset.get_result(result.proc_tool)
        refine_tool_entry = _update_result_entry(
            project, dataset, tool, result.status, proc_tool_entry
        )
        if result.status == ToolStatus.SUCCESS:
            _update_refine_result_entry(project, refine_tool_entry, result)


def update_ligfit_tool_status(project: Project, tool: str, dataset):
    for result in scrape_ligfit_results(project, tool, dataset):
        proc_tool_entry = dataset.get_result(result.proc_tool)
        refine_tool_entry = dataset.get_result(result.refine_tool, proc_tool_entry)
        ligfit_tool_entry = _update_result_entry(
            project, dataset, tool, result.status, refine_tool_entry
        )
        if result.status == ToolStatus.SUCCESS:
            _update_ligfit_result_entry(project, ligfit_tool_entry, result)


def scrape_imported_autoproc_status(project: Project):
    tools = _supported_autoproc_tools()

    if not tools:
        # this site does not support importing
        # any auto-processed data, nothing to do here
        return

    for dset in project.get_datasets():
        for tool in tools:
            update_proc_tool_status(project, tool, dset)
