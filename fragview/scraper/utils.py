from typing import Iterator
from pathlib import Path


def split_unit_cell_vals(unit_cell):
    """
    split unit cell values into 'dim' and 'ang' parts
    """
    vals = unit_cell.split(",")
    return dict(dim=vals[:3], ang=vals[3:])


def get_files_by_suffixes(dir: Path, file_suffixes) -> Iterator[Path]:
    for child in dir.iterdir():
        if not child.is_file():
            continue

        suffix = child.suffix[1:].lower()
        if suffix in file_suffixes:
            yield child
