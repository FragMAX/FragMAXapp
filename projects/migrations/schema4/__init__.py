from pony.orm import Database, db_session


def add_beamline_column(db: Database):
    db.execute(
        "alter table DataSet add column beamline text not null default 'unknown'"
    ).close()


def rename_proc_columns(db: Database):
    db.execute(
        "alter table ProcessResult rename low_resolution_average to low_resolution_overall"
    ).close()

    db.execute(
        "alter table ProcessResult rename high_resolution_average to high_resolution_overall"
    ).close()


def drop_dataset_resolution_column(db: Database):
    db.execute("alter table DataSet drop column resolution").close()


@db_session
def migrate(db: Database, project_desc):
    """
    migrate project database from schema ver 4 to ver 5
    """
    add_beamline_column(db)
    rename_proc_columns(db)
    drop_dataset_resolution_column(db)
