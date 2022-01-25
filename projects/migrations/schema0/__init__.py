from pony.orm import Database
from projects.migrations import ProjectDesc
from projects.migrations.schema0.pdb import migrate_pdb_table
from projects.migrations.schema0.mtzs import migrate_process_result_table


def migrate(db: Database, project_desc: ProjectDesc):
    """
    migrate project database from schema ver 0 to ver 1
    """

    migrate_pdb_table(db, project_desc)
    # note that PDB table must be migrated first, as the
    # migration code needs a database in schema v1 format
    migrate_process_result_table(project_desc)
