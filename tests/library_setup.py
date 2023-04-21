from dataclasses import dataclass
from fragview import models


@dataclass
class Fragment:
    code: str
    smiles: str


@dataclass
class Library:
    name: str
    fragments: list[Fragment]


def create_library(library: Library):
    db_lib = models.Library(name=library.name)
    db_lib.save()

    for fragment in library.fragments:
        db_frag = models.Fragment(
            library=db_lib, code=fragment.code, smiles=fragment.smiles
        )
        db_frag.save()

    return db_lib
