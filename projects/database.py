from pathlib import Path
from pony.orm import Database, db_session, desc
from projects.models import _define_entities
import conf


class ProjectNotFound(Exception):
    pass


def _bind(db_file: Path, create_tables=False) -> Database:
    db = Database()
    _define_entities(db)

    db.bind(provider="sqlite", filename=str(db_file))
    db.generate_mapping(create_tables=create_tables)

    return db


def _db_file(project_id: str) -> Path:
    return Path(conf.PROJECTS_DB_DIR, f"proj{project_id}.db")


def create_project_db(project_id: str, proposal, protein) -> Database:
    db_file = _db_file(project_id)
    if db_file.is_file():
        raise Exception(f"{db_file}: already exists")
    db_file.touch()

    db = _bind(db_file, create_tables=True)
    with db_session:
        db.Project(protein=protein, proposal=proposal)

    return db


def get_project_db(project_id) -> Database:
    db_file = _db_file(project_id)
    if not db_file.is_file():
        raise ProjectNotFound(f"{db_file}: database file not found")

    return _bind(db_file)
