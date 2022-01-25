from typing import Optional
from pathlib import Path
from pony.orm import Database, db_session
from projects.models import _define_entities

#
# make it possible for the client code to
# import the misc database related symbols
# from 'projects.database' module, in order
# to add an abstraction layer above 'ponyORM'
#
from pony.orm import desc, commit  # noqa F401
from pony.orm import TransactionIntegrityError  # noqa F401


class ProjectNotFound(Exception):
    pass


def _bind(db_file: Path, create_tables=False) -> Database:
    db = Database()
    _define_entities(db)

    db.bind(provider="sqlite", filename=str(db_file))
    db.generate_mapping(create_tables=create_tables)

    return db


def get_project_db_file(projects_db_dir: Path, project_id: str) -> Path:
    return Path(projects_db_dir, f"proj{project_id}.db")


def create_project_db(
    projects_db_dir: Path,
    project_id: str,
    proposal: str,
    protein: str,
    encryption_key: Optional[bytes],
) -> Database:
    db_file = get_project_db_file(projects_db_dir, project_id)
    if db_file.is_file():
        raise Exception(f"{db_file}: already exists")

    db_file.parent.mkdir(exist_ok=True)
    db_file.touch()

    db = _bind(db_file, create_tables=True)
    with db_session:
        encrypted = encryption_key is not None
        db.Project(
            protein=protein,
            proposal=proposal,
            encrypted=encrypted,
            encryption_key=encryption_key,
        )

    return db


def get_project_db(projects_db_dir: Path, project_id: str) -> Database:
    db_file = get_project_db_file(projects_db_dir, project_id)
    if not db_file.is_file():
        raise ProjectNotFound(f"{db_file}: database file not found")

    return _bind(db_file)
