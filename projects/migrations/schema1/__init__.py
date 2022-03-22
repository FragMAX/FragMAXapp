from pony.orm import Database, db_session
from projects.migrations import ProjectDesc


@db_session
def migrate(db: Database, project_desc: ProjectDesc):
    """
    migrate project database from schema ver 1 to ver 2
    """
    db.execute(
        """CREATE TABLE IF NOT EXISTS "Author" (
          "id" INTEGER PRIMARY KEY AUTOINCREMENT,
          "orcid" TEXT NOT NULL,
          "name" TEXT NOT NULL
        )"""
    ).close()

    db.execute(
        """CREATE TABLE IF NOT EXISTS "Scientist" (
          "id" INTEGER PRIMARY KEY AUTOINCREMENT,
          "orcid" TEXT NOT NULL,
          "salutation" TEXT NOT NULL,
          "first_name" TEXT NOT NULL,
          "last_name" TEXT NOT NULL,
          "role" TEXT NOT NULL,
          "organization_type" TEXT NOT NULL,
          "organization_name" TEXT NOT NULL,
          "street" TEXT NOT NULL,
          "city" TEXT NOT NULL,
          "zip_code" TEXT NOT NULL,
          "country" TEXT NOT NULL,
          "email" TEXT NOT NULL,
          "phone" TEXT NOT NULL
        )"""
    ).close()

    db.execute(
        """CREATE TABLE IF NOT EXISTS "Details" (
          "id" INTEGER PRIMARY KEY AUTOINCREMENT,
          "sequence_release" TEXT NOT NULL,
          "coordinates_release" TEXT NOT NULL,
          "deposition_title" TEXT NOT NULL,
          "description" TEXT NOT NULL,
          "keywords" TEXT NOT NULL,
          "biological_assembly" TEXT NOT NULL,
          "structure_title" TEXT NOT NULL,
          "deposit_pandda" BOOLEAN NOT NULL,
          "apo_structure_title" TEXT NOT NULL,
          "starting_model" TEXT NOT NULL,
          "principal_investigator" INTEGER REFERENCES "Scientist" ("id") ON DELETE SET NULL
        )"""
    ).close()

    db.execute(
        "INSERT INTO Details VALUES(1,'','','','','','','',0,'','',NULL)"
    ).close()

    db.execute(
        """CREATE TABLE IF NOT EXISTS "Funding" (
          "id" INTEGER PRIMARY KEY AUTOINCREMENT,
          "organization" TEXT NOT NULL,
          "grant_number" TEXT NOT NULL
        )"""
    ).close()

    db.execute(
        """CREATE TABLE IF NOT EXISTS "ProteinEntity" (
          "id" INTEGER PRIMARY KEY AUTOINCREMENT,
          "uniprot_id" TEXT NOT NULL,
          "sequence" TEXT NOT NULL
        )"""
    ).close()
