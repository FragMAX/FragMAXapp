from pathlib import Path
from dataclasses import dataclass
from gemmi import read_pdb
from pony.orm import Database, db_session
from fragview.space_groups import space_group_to_db_format
from projects.migrations import ProjectDesc


@dataclass
class PDBRow:
    id: int
    filename: str
    pdb_id: str
    space_group: str
    unit_cell_a: float
    unit_cell_b: float
    unit_cell_c: float
    unit_cell_alpha: float
    unit_cell_beta: float
    unit_cell_gamma: float


def _load_pdb(pdb_filename: str, project_paths: ProjectDesc):
    pdb_path = Path(project_paths.models_dir, pdb_filename)
    return read_pdb(str(pdb_path))


def _get_pdb_rows(db: Database, project_paths: ProjectDesc):
    # get all PDB entries from the database
    pdbs = db.select("select id, filename, pdb_id from PDB")

    for row_id, filename, pdb_id in pdbs:
        pdb = _load_pdb(filename, project_paths)
        space_group = pdb.find_spacegroup()
        if space_group is None:
            print(f"WARNING: no space group listed in {filename}, dropping that file")
            continue

        yield PDBRow(
            row_id,
            filename,
            pdb_id,
            space_group_to_db_format(space_group),
            unit_cell_a=pdb.cell.a,
            unit_cell_b=pdb.cell.b,
            unit_cell_c=pdb.cell.c,
            unit_cell_alpha=pdb.cell.alpha,
            unit_cell_beta=pdb.cell.beta,
            unit_cell_gamma=pdb.cell.gamma,
        )


def _recreate_table(db: Database):
    # drop PDB table, so that can re-create it with new 'NOT NULL' columns
    db.execute("drop table PDB").close()

    # re-create table, with new space_group and unit_cell_* columns
    db.execute(
        """CREATE TABLE IF NOT EXISTS "PDB" (
              "id" INTEGER PRIMARY KEY AUTOINCREMENT,
              "filename" TEXT UNIQUE NOT NULL,
              "pdb_id" TEXT NOT NULL,
              "space_group" TEXT NOT NULL,
              "unit_cell_a" REAL NOT NULL,
              "unit_cell_b" REAL NOT NULL,
              "unit_cell_c" REAL NOT NULL,
              "unit_cell_alpha" REAL NOT NULL,
              "unit_cell_beta" REAL NOT NULL,
              "unit_cell_gamma" REAL NOT NULL)"""
    ).close()


def _repopulate_table(db: Database, pdb_rows: list[PDBRow]):
    for row in pdb_rows:
        db.execute(
            "insert into PDB("
            "   id, filename, pdb_id, space_group, "
            "   unit_cell_a, unit_cell_b, unit_cell_c,"
            "   unit_cell_alpha, unit_cell_beta, unit_cell_gamma) "
            "values("
            f'  {row.id}, "{row.filename}", "{row.pdb_id}", "{row.space_group}",'
            f"  {row.unit_cell_a}, {row.unit_cell_b}, {row.unit_cell_c}, "
            f"  {row.unit_cell_alpha}, {row.unit_cell_beta}, {row.unit_cell_gamma})"
        ).close()


@db_session
def migrate_pdb_table(db: Database, project_paths: ProjectDesc):
    # store in-memory rows we'll put into migrated PDB table
    pdb_rows = list(_get_pdb_rows(db, project_paths))

    _recreate_table(db)
    _repopulate_table(db, pdb_rows)
