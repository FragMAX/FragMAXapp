"""
scrape PHENIX ligandfit logs
"""
from typing import Union, Tuple, TextIO
from pathlib import Path
from fragview.dsets import ToolStatus
from fragview.fileio import subdirs
from fragview.projects import project_results_dataset_dir

SECTION_LINE = "This fit is the new best one..."
SCORE_LINE = " cc_overall "
BLOB_LINE = " lig_xyz "


def _no_results() -> Tuple[None, None]:
    return None, None


def _parse_section(ligfit_log: TextIO):
    score = None
    blob = None

    for line in ligfit_log:
        if line.strip() == "":
            # empty line is the end of the 'section'
            break

        if line.startswith(SCORE_LINE):
            score = line[len(SCORE_LINE) :].strip()
        elif line.startswith(BLOB_LINE):
            blob = line[len(BLOB_LINE) :].strip()

    return score, blob


def _parse_ligfit_log(ligfit_log: TextIO):
    score = None
    blob = None

    for line in ligfit_log:
        if line.startswith(SECTION_LINE):
            score, blob = _parse_section(ligfit_log)

    return score, blob


def scrape_score_blob(result_dir: Path) -> Union[Tuple[None, None]]:
    """
    scrape ligfit score and ligand blob coordinates
    """
    ligfit_dir = Path(result_dir, "ligfit", "LigandFit_run_1_")
    if not ligfit_dir.is_dir():
        return _no_results()

    ligfit_log = Path(ligfit_dir, "LigandFit_run_1_1.log")
    if not ligfit_log.is_file():
        return _no_results()

    with ligfit_log.open() as f:
        return _parse_ligfit_log(f)


def scrape_outcome(project, dataset: str) -> ToolStatus:
    res_dir = project_results_dataset_dir(project, dataset)

    for ref_dir in subdirs(res_dir, 2):
        score, _ = scrape_score_blob(ref_dir)
        if score is not None:
            return ToolStatus.SUCCESS

        if Path(ref_dir, "ligfit", "LigandFit_run_1_").is_dir():
            return ToolStatus.FAILURE

    return ToolStatus.UNKNOWN
