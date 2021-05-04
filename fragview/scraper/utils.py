from typing import Optional, Iterable, List
from pathlib import Path
from fragview.projects import project_results_dataset_dir
from fragview.fileio import subdirs


def get_files_by_suffixes(
    dir: Path, file_suffixes: List[str]
) -> Optional[Iterable[Path]]:
    for child in dir.iterdir():
        if not child.is_file():
            continue

        suffix = child.suffix[1:].lower()
        if suffix in file_suffixes:
            yield child


def get_final_pdbs(project, dataset, refine_tool: str):
    res_dir = project_results_dataset_dir(project, dataset)

    for sdir in subdirs(res_dir, 2):
        if sdir.name != refine_tool:
            continue

        final_pdb = Path(sdir, "final.pdb")
        if final_pdb.is_file():
            yield final_pdb
