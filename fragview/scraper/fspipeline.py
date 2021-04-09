import re
from typing import List
from pathlib import Path
from gemmi import read_pdb
from fragview.dsets import ToolStatus
from fragview.fileio import read_text_lines
from fragview.projects import project_results_dataset_dir
from fragview.scraper.utils import get_final_pdbs
from fragview.scraper import rhofit, ligandfit
from fragview.scraper.proc_logs import scrape_isa

# regexp used to extract r-work, r-free, etc values from PDB comments
REM_FINAL_RE = re.compile(
    r"REMARK Final: r_work = ([0-9.]*) r_free = ([0-9.]*) bonds = ([0-9.]*) angles = ([0-9.]*)"
)

# regexp used to extract blob coordinates from blobs.log files
CLUSTER_RE = re.compile(
    r"INFO:: cluster at xyz = \(\s*([\d\\.-]*),\s*([\d\\.-]*),\s*([\d\\.-]*)"
)


def scrape_outcome(project, dataset) -> ToolStatus:
    res_dir = project_results_dataset_dir(project, dataset)

    for sdir in res_dir.glob("*/fspipeline"):
        if Path(sdir, "final.pdb").is_file():
            return ToolStatus.SUCCESS

    res_subdirs = list(res_dir.glob("*/fspipeline"))
    if res_subdirs:
        return ToolStatus.FAILURE

    return ToolStatus.UNKNOWN


def _parse_pdb(pdb: Path):
    struct = read_pdb(str(pdb))
    r_work = None
    r_free = None
    bonds = None
    angles = None

    #
    # look for 'REMARK Final:' remark line
    # which specifies r-work, r-free, bonds and angles values
    #
    for rem in struct.raw_remarks:
        match = REM_FINAL_RE.match(rem)
        if match is None:
            continue

        # remark line found, get our values and end the loop
        r_work, r_free, bonds, angles = match.groups()
        break

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


def _scrape_blobs(project, res_dir: Path) -> List[List[float]]:
    blobs_log = Path(res_dir, "blobs.log")
    if not blobs_log.is_file():
        return []

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

    return blobs


def _get_results(project, dataset, final_pdb: Path):
    parent_dir = final_pdb.parent

    proc_tool = parent_dir.parent.name

    isa = scrape_isa(project, proc_tool, dataset)

    dif_map = Path(parent_dir, "final_2mFo-DFc.ccp4")
    nat_map = Path(parent_dir, "final_mFo-DFc.ccp4")

    spacegroup, resolution, r_work, r_free, bonds, angles, cell = _parse_pdb(final_pdb)

    blobs = _scrape_blobs(project, parent_dir)
    rhofit_score = rhofit.scrape_score(parent_dir)
    ligfit_score, ligblob = ligandfit.scrape_score_blob(parent_dir)

    return (
        proc_tool,
        str(dif_map),
        str(nat_map),
        spacegroup,
        resolution,
        isa,
        r_work,
        r_free,
        bonds,
        angles,
        cell.a,
        cell.b,
        cell.c,
        cell.alpha,
        cell.beta,
        cell.gamma,
        blobs,
        rhofit_score,
        ligfit_score,
        ligblob,
    )


def scrape_results(project, dataset):
    for final_pdb in get_final_pdbs(project, dataset, "fspipeline"):
        yield _get_results(project, dataset, final_pdb)
