from pony.orm import Database, db_session


@db_session
def migrate(db: Database, project_desc):
    """
    migrate project database from schema ver 3 to ver 4
    """
    # drop encryption related columns
    db.execute("alter table Project drop column encrypted").close()
    db.execute("alter table Project drop column encryption_key").close()
