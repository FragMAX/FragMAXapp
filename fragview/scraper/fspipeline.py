from typing import Iterator
import re
from pathlib import Path
from gemmi import read_pdb, Structure
from fragview.fileio import read_text_lines
from fragview.projects import Project
from fragview.scraper import ToolStatus, RefineResult

# regexp used to extract R-work, R-free, bonds and agnles values
REM_R_WORK = re.compile(r"REMARK   3   R VALUE            \(WORKING SET\) : ([0-9\.]+)")
REM_R_FREE = re.compile(r"REMARK   3   FREE R VALUE                     : ([0-9\.]+)")
REM_BONDS = re.compile(r"REMARK   3    BOND      :  ([0-9\.]+)")
REM_ANGLES = re.compile(r"REMARK   3    ANGLE     :  ([0-9\.]+)")

# regexp used to extract blob coordinates from blobs.log files
CLUSTER_RE = re.compile(
    r"INFO:: cluster at xyz = \(\s*([\d\\.-]*),\s*([\d\\.-]*),\s*([\d\\.-]*)"
)


def _parse_stats(pdb: Structure):
    r_work = None
    r_free = None
    bonds = None
    angles = None

    for rem in pdb.raw_remarks:
        match = REM_R_WORK.match(rem)
        if match:
            (r_work,) = match.groups()

        match = REM_R_FREE.match(rem)
        if match:
            (r_free,) = match.groups()

        match = REM_BONDS.match(rem)
        if match:
            (bonds,) = match.groups()

        match = REM_ANGLES.match(rem)
        if match:
            (angles,) = match.groups()

    return r_work, r_free, bonds, angles


def _parse_pdb(pdb: Path):
    struct = read_pdb(str(pdb))
    r_work, r_free, bonds, angles = _parse_stats(struct)

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


def _scrape_blobs(project, results_dir: Path) -> str:
    blobs_log = Path(results_dir, "blobs.log")
    if not blobs_log.is_file():
        return "[]"

    blobs = []

    #
    # look for 'INFO:: cluster at xyz ...' lines in the blobs.log file,
    # and parse out blob coordinates
    #
    for line in read_text_lines(project, blobs_log):
        match = CLUSTER_RE.match(line)
        if match is None:
            continue

        x, y, z = match.groups()
        blobs.append([float(x), float(y), float(z)])

    return str(blobs)


def _get_results(project, dataset, results_dir: Path) -> RefineResult:
    proc_tool = results_dir.parent.name
    final_pdb = Path(results_dir, "final.pdb")
    result = RefineResult(proc_tool, "fspipeline")

    if final_pdb.is_file():
        result.status = ToolStatus.SUCCESS
    else:
        result.status = ToolStatus.FAILURE

    if result.status == ToolStatus.FAILURE:
        return result

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

    for sdir in res_dir.glob("*/fspipeline"):
        yield _get_results(project, dataset, sdir)


def get_refine_log_files(project: Project, dataset, processing_tool) -> Iterator[Path]:
    res_dir = Path(
        project.get_dataset_results_dir(dataset), processing_tool, "fspipeline"
    )
    project_dir = project.project_dir

    for path in res_dir.glob("**/*.log"):
        if path.is_file():
            yield path.relative_to(project_dir)
