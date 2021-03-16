from pathlib import Path
from gemmi import read_pdb
from fragview.projects import project_results_dataset_dir, project_process_dataset_dir
from fragview.dsets import ToolStatus
from fragview.fileio import subdirs, read_text_lines
from fragview.scraper.proc_logs import scrape_proc_logs

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


def scrape_outcome(project, dataset) -> ToolStatus:
    res_dir = project_results_dataset_dir(project, dataset)

    res_subdirs = list(res_dir.glob("*/dimple"))
    for sdir in res_dir.glob("*/dimple"):
        if Path(sdir, "final.pdb").is_file():
            return ToolStatus.SUCCESS

    if res_subdirs:
        return ToolStatus.FAILURE

    return ToolStatus.UNKNOWN


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


def _get_final_pdbs(project, dataset):
    res_dir = project_results_dataset_dir(project, dataset)

    for sdir in subdirs(res_dir, 2):
        final_pdb = Path(sdir, "final.pdb")
        if final_pdb.is_file():
            yield final_pdb


def _scrape_blobs(project, logs_dir):
    for line in read_text_lines(project, Path(logs_dir, "dimple.log")):
        if line.startswith(BLOBS_LINE):
            return _cut_prefix_strip(BLOBS_LINE, line)


def _get_results(project, dataset, final_pdb: Path):
    parent_dir = final_pdb.parent

    proc_tool = parent_dir.parent.name
    proc_dir = Path(project_process_dataset_dir(project, dataset), proc_tool)
    isa = scrape_proc_logs(project, proc_dir)

    dif_map = Path(parent_dir, "final_2mFo-DFc.ccp4")
    nat_map = Path(parent_dir, "final_mFo-DFc.ccp4")

    spacegroup, resolution, r_work, r_free, bonds, angles, cell = _parse_pdb(final_pdb)

    blobs = _scrape_blobs(project, parent_dir)

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
    )


def scrape_results(project, dataset):
    for final_pdb in _get_final_pdbs(project, dataset):
        yield _get_results(project, dataset, final_pdb)
