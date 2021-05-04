from typing import Iterator, Iterable, Optional
from pathlib import Path
from gemmi import read_pdb
from fragview.projects import Project
from fragview.fileio import read_text_lines
from fragview.scraper import ToolStatus, RefineResult
from fragview.scraper.utils import get_files_by_suffixes

#
# PDB remark line prefixes we use for parsing
#
R_WORK_LINE = "REMARK   3   R VALUE            (WORKING SET) :"
R_FREE_LINE = "REMARK   3   FREE R VALUE                     :"
BONDS_LINE = "REMARK   3   BOND LENGTHS REFINED ATOMS        (A):"
ANGLES_LINE = "REMARK   3   BOND ANGLES REFINED ATOMS   (DEGREES):"

#
# dimple log line prefix we use for parsing
#
BLOBS_LINE = "blobs:"


def _cut_prefix_strip(prefix, line):
    return line[len(prefix) :].strip()


def _parse_pdb(pdb: Path):
    struct = read_pdb(str(pdb))
    r_work = None
    r_free = None
    bonds = None
    angles = None

    for rem in struct.raw_remarks:
        if rem.startswith(R_WORK_LINE):
            r_work = _cut_prefix_strip(R_WORK_LINE, rem)
        if rem.startswith(R_FREE_LINE):
            r_free = _cut_prefix_strip(R_FREE_LINE, rem)
        if rem.startswith(BONDS_LINE):
            bonds = _cut_prefix_strip(BONDS_LINE, rem)
            bonds = bonds.split(";")[1].strip()
        if rem.startswith(ANGLES_LINE):
            angles = _cut_prefix_strip(ANGLES_LINE, rem)
            angles = angles.split(";")[1].strip()

    # remove all spaces from the space group specification,
    # e.g. 'P 1 21 1' becomes 'P1211'
    spacegroup = "".join(struct.spacegroup_hm.split(" "))

    return (
        spacegroup,
        struct.resolution,
        r_work,
        r_free,
        bonds,
        angles,
        struct.cell,
    )


def _scrape_blobs(project, logs_dir):
    for line in read_text_lines(project, Path(logs_dir, "dimple.log")):
        if line.startswith(BLOBS_LINE):
            return _cut_prefix_strip(BLOBS_LINE, line)


def _get_results(project: Project, dataset, results_dir: Path) -> RefineResult:
    proc_tool = results_dir.parent.name
    final_pdb = Path(results_dir, "final.pdb")

    if not final_pdb.is_file():
        # looks like refine job failed
        return RefineResult(proc_tool, "dimple", ToolStatus.FAILURE)

    result = RefineResult(proc_tool, "dimple", ToolStatus.SUCCESS)

    (
        result.space_group,
        result.resolution,
        result.r_work,
        result.r_free,
        result.rms_bonds,
        result.rms_angles,
        result.cell,
    ) = _parse_pdb(final_pdb)

    result.blobs = _scrape_blobs(project, results_dir)

    return result


def scrape_results(project: Project, dataset) -> Iterator[RefineResult]:
    res_dir = project.get_dataset_results_dir(dataset)

    for sdir in res_dir.glob("*/dimple"):
        yield _get_results(project, dataset, sdir)


def get_refine_log_files(
    project: Project, dataset, processing_tool
) -> Optional[Iterable[Path]]:
    res_dir = Path(project.get_dataset_results_dir(dataset), processing_tool, "dimple")

    return get_files_by_suffixes(res_dir, ["log"])
