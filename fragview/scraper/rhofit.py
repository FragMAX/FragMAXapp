from typing import Union
from pathlib import Path
from fragview.dsets import ToolStatus
from fragview.fileio import subdirs
from fragview.projects import project_results_dataset_dir


def scrape_score(result_dir: Path) -> Union[None, str]:
    rho_dir = Path(result_dir, "rhofit")
    if not rho_dir.is_dir():
        # no rhofit directory found, no score available
        return None

    hit_log = Path(rho_dir, "Hit_corr.log")
    if not hit_log.is_file():
        # no 'hit corr' log found, no score available
        return None

    with hit_log.open() as f:
        first_line = f.readline().strip()

    _, score = first_line.rsplit(" ", 2)

    return score


def scrape_outcome(project, dataset: str) -> ToolStatus:
    res_dir = project_results_dataset_dir(project, dataset)

    for ref_dir in subdirs(res_dir, 2):
        score = scrape_score(ref_dir)
        if score is not None:
            return ToolStatus.SUCCESS

        if Path(ref_dir, "rhofit").is_dir():
            return ToolStatus.FAILURE

    return ToolStatus.UNKNOWN
