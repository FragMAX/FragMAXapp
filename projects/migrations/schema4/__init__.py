from pony.orm import Database, db_session


def add_beamline_column(db: Database):
    db.execute(
        "alter table DataSet add column beamline text not null default 'unknown'"
    ).close()


@db_session
def migrate(db: Database, project_desc):
    """
    migrate project database from schema ver 4 to ver 5
    """
    add_beamline_column(db)
