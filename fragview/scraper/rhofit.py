from typing import Union, Iterator
from pathlib import Path
from fragview.scraper import ToolStatus, LigfitResult
from fragview.fileio import subdirs
from fragview.projects import Project


def _scrape_score(result_dir: Path) -> Union[None, str]:
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


def scrape_results(project: Project, dataset) -> Iterator[LigfitResult]:
    res_dir = project.get_dataset_results_dir(dataset)

    for ref_dir in subdirs(res_dir, 2):
        score = _scrape_score(ref_dir)
        proc_tool = ref_dir.parent.name
        refine_tool = ref_dir.name
        if score is None:
            status = ToolStatus.FAILURE
        else:
            status = ToolStatus.SUCCESS
        yield LigfitResult(proc_tool, refine_tool, "rhofit", status, score)
