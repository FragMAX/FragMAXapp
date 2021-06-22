from typing import Iterator, List
from pathlib import Path
from fragview.projects import Project
from fragview.fileio import subdirs


def get_files_by_suffixes(dir: Path, file_suffixes: List[str]) -> Iterator[Path]:
    for child in dir.iterdir():
        if not child.is_file():
            continue

        suffix = child.suffix[1:].lower()
        if suffix in file_suffixes:
            yield child


# TODO: remove me?
def get_final_pdbs(project: Project, dataset, refine_tool: str):
    res_dir = project.get_dataset_results_dir(dataset)

    for sdir in subdirs(res_dir, 2):
        if sdir.name != refine_tool:
            continue

        final_pdb = Path(sdir, "final.pdb")
        if final_pdb.is_file():
            yield final_pdb
