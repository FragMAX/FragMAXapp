from typing import Optional, Iterable, List
from pathlib import Path
from gemmi import read_mtz_file
from fragview.scraper import ProcStats
from fragview.space_groups import space_group_to_db_format


def get_files_by_suffixes(
    dir: Path, file_suffixes: List[str]
) -> Optional[Iterable[Path]]:
    for child in dir.iterdir():
        if not child.is_file():
            continue

        suffix = child.suffix[1:].lower()
        if suffix in file_suffixes:
            yield child


def load_mtz_stats(mtz_path: Path, stats: ProcStats):
    mtz = read_mtz_file(str(mtz_path))

    stats.space_group = space_group_to_db_format(mtz.spacegroup)
    stats.unit_cell_a = mtz.cell.a
    stats.unit_cell_b = mtz.cell.b
    stats.unit_cell_c = mtz.cell.c
    stats.unit_cell_alpha = mtz.cell.alpha
    stats.unit_cell_beta = mtz.cell.beta
    stats.unit_cell_gamma = mtz.cell.gamma
