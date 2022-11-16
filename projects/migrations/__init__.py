from pathlib import Path
from dataclasses import dataclass


@dataclass
class ProjectDesc:
    project_id: str
    project_db_file: Path
    project_dir: Path
    models_dir: Path
