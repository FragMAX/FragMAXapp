from pathlib import Path
from shutil import copyfile
from importlib import import_module
from dataclasses import dataclass
from pony.orm import Database
from django.core.management.base import BaseCommand
from django.conf import settings
from fragview.models import UserProject
from fragview.sites.current import get_project_dir
from projects.migrations import ProjectDesc
from projects.models import LATEST_SCHEMA_VERSION
from projects.database import db_session, get_project_db_file


@db_session
def _get_schema_version(db: Database) -> int:
    res = db.select("select db_schema_version from Project")
    return int(res[0])


@db_session
def _set_schema_version(db: Database, new_schema_version):
    db.execute(f"update Project set db_schema_version='{new_schema_version}'")


def _migrate_project(
    current_schema_version: int,
    db: Database,
    project_paths: ProjectDesc,
):
    # backup current db file
    backup_file = f"{project_paths.project_db_file}-v{current_schema_version}-backup"
    copyfile(project_paths.project_db_file, backup_file)

    # call schema migration code
    mod_name = f"projects.migrations.schema{current_schema_version}"
    import_module(mod_name).migrate(db, project_paths)  # type: ignore

    # update schema version entry
    _set_schema_version(db, current_schema_version + 1)


@dataclass
class FauxProject:
    id: int


def _get_project_desc(user_proj: UserProject) -> ProjectDesc:
    #
    # get project files directory, using a 'fake' project object
    # we can't use real Project class instance here,
    # because creating such object will fail due to changed database schema
    #
    project_dir = get_project_dir(FauxProject(id=user_proj.id))
    project_db_file = get_project_db_file(settings.PROJECTS_DB_DIR, user_proj.id)

    return ProjectDesc(
        project_id=str(user_proj.id),
        project_db_file=project_db_file,
        project_dir=project_dir,
        models_dir=Path(project_dir, "models"),
    )


def _migrate_all():
    #
    # For all project database files, apply schema migrations if needed
    #
    for user_proj in UserProject.objects.all():
        project_desc = _get_project_desc(user_proj)

        db = Database()
        db.bind(
            provider="sqlite",
            filename=str(project_desc.project_db_file),
        )
        schema_version = _get_schema_version(db)

        print(f"{project_desc.project_db_file}, schema version: {schema_version}")

        for n in range(schema_version, int(LATEST_SCHEMA_VERSION)):
            print(f"migrating schema version {n} -> {n+1}")
            _migrate_project(schema_version, db, project_desc)


class Command(BaseCommand):
    help = f"migrate project databases to schema version {LATEST_SCHEMA_VERSION}"

    def handle(self, *args, **options):
        _migrate_all()
