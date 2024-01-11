from typing import Iterator, Iterable
from pathlib import Path
from django.shortcuts import render
from fragview.projects import Project, current_project
from fragview.scraper import PROC_TOOLS, get_processing_log_files, get_refine_log_files
from fragview.sites import SITE
from fragview.views.utils import get_dataset_by_id
from fragview.views.wrap import (
    ProcessingInfo,
    DatasetInfo,
    wrap_refine_results,
    Wrapper,
)


class FSPipelineLogPath(Wrapper):
    """
    special case wrapper for FSpipeline logs

    We show fspipeline logs in subdirectories,
    so we need to show relative parent folder as well.

    This wrapper overrides 'name' property, to include parent
    directory name.
    """

    @property
    def name(self):
        results_root_dir = list(self.orig.parents)[-5]
        return str(self.orig.relative_to(results_root_dir))

    def __lt__(self, other):
        """
        make wrapper objects sortable
        """
        return self.name < other.name

    def __str__(self):
        return str(self.orig)


def _get_processing_info(project: Project, dataset) -> Iterator[ProcessingInfo]:
    for proc_res in project.get_datasets_process_results(dataset):
        yield ProcessingInfo(proc_res)


def _get_relative_path(project: Project, dataset, log_file: Path) -> Path:
    dset_root_dir = project.get_dataset_root_dir(dataset)
    if log_file.is_relative_to(dset_root_dir):
        return log_file.relative_to(dset_root_dir)

    dset_proc_dir = project.get_dataset_process_dir(dataset)
    if log_file.is_relative_to(dset_proc_dir):
        return log_file.relative_to(dset_proc_dir)

    dset_res_dir = project.get_dataset_results_dir(dataset)
    if log_file.is_relative_to(dset_res_dir):
        return log_file.relative_to(dset_res_dir)

    assert False, f"unexpected path {log_file}"


def _as_relative_paths(
    project: Project, dataset, log_files: Iterable[Path]
) -> Iterable[Path]:
    for log_file in log_files:
        yield _get_relative_path(project, dataset, log_file)


def _get_processing_logs(project: Project, dataset) -> dict[str, Iterable[Path]]:
    logs = {}
    for tool in PROC_TOOLS:
        if dataset.tool_result(tool) is None:
            continue

        log_files = get_processing_log_files(project, tool, dataset)
        if log_files is None:
            # no log files found
            continue

        logs[tool] = _as_relative_paths(project, dataset, log_files)

    return logs


def _get_refine_logs(project: Project, dataset):
    def _add_logs(proc_tool, ref_tool, log_files):
        if ref_tool not in logs:
            logs[ref_tool] = {}

        logs[ref_tool][proc_tool] = _as_relative_paths(project, dataset, log_files)

    logs: dict[str, list] = {}

    for ref_result in project.get_datasets_refine_results(dataset):
        log_files = get_refine_log_files(
            project, dataset, ref_result.process_tool, ref_result.refine_tool
        )

        if ref_result.refine_tool == "fspipeline":
            # wrap fspipeline logs into custom object, to handle
            # log files inside subdirectories
            log_files = [FSPipelineLogPath(log) for log in log_files]  # type: ignore

        _add_logs(ref_result.process_tool, ref_result.refine_tool, sorted(log_files))

    return logs


def show(request, dataset_id):
    project = current_project(request)

    dataset = get_dataset_by_id(project, dataset_id)

    # must be a list, as template needs to iterate over this multiple times
    processing_stats = list(_get_processing_info(project, dataset))

    return render(
        request,
        "dataset_info.html",
        {
            "dataset": DatasetInfo(dataset),
            "processing_stats": processing_stats,
            "refine_results": wrap_refine_results(
                project.get_datasets_refine_results(dataset)
            ),
            "energy": 12.4 / dataset.wavelength,
            "total_rotation": dataset.images * dataset.angle_increment,
            "proc_logs": _get_processing_logs(project, dataset),
            "refine_logs": _get_refine_logs(project, dataset),
            "site": SITE,
            "beamline": SITE.get_beamline_info(),
        },
    )
