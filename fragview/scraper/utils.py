from typing import Optional, Iterable, List
from pathlib import Path


def get_files_by_suffixes(
    dir: Path, file_suffixes: List[str]
) -> Optional[Iterable[Path]]:
    for child in dir.iterdir():
        if not child.is_file():
            continue

        suffix = child.suffix[1:].lower()
        if suffix in file_suffixes:
            yield child
