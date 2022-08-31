from pony.orm import Database
from pony.orm import PrimaryKey, Required, Optional, Set

#
# provides a limited API to access old-style fragmax databases
#


def _define_entities(db):
    class Library(db.Entity):
        _table_ = "fragview_library"
        id = PrimaryKey(int)
        name = Required(str)
        project = Optional(lambda: Project)
        fragments = Set(lambda: Fragment)

    class Fragment(db.Entity):
        _table_ = "fragview_fragment"
        id = PrimaryKey(int)
        name = Required(str)
        smiles = Required(str)
        library = Required(Library, column="library_id")

    class Project(db.Entity):
        _table_ = "fragview_project"
        id = PrimaryKey(int)
        protein = Required(str)
        proposal = Required(str)
        # library_id = Required(int)
        library = Required(Library, column="library_id")


def lookup_project(db, protein: str, proposal: str):
    """
    lookup project by protein and proposal
    """

    projs = db.Project.select(protein=protein, proposal=proposal)

    assert len(projs) == 1, "expected 1 project match"

    return projs.first()


def bind(db_file):
    db = Database()
    _define_entities(db)

    db.bind(provider="sqlite", filename=db_file)
    db.generate_mapping(create_tables=False)

    return db
