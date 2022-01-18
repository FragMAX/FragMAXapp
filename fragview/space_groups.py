from typing import Optional
import gemmi
from enum import Enum, auto
from dataclasses import dataclass


class System(Enum):
    TRICLINIC = auto()
    MONOCLINIC = auto()
    ORTHORHOMBIC = auto()
    TETRAGONAL = auto()
    TRIGONAL = auto()
    HEXAGONAL = auto()
    RHOMBOHEDRAL = auto()
    CUBIC = auto()


@dataclass
class SpaceGroup:
    system: System
    short_name: str
    number: int


SPACE_GROUPS = [
    # Triclinic
    SpaceGroup(System.TRICLINIC, "P1", 1),
    # Monoclinic
    SpaceGroup(System.MONOCLINIC, "P2", 3),
    SpaceGroup(System.MONOCLINIC, "P21", 4),
    SpaceGroup(System.MONOCLINIC, "C2", 5),
    SpaceGroup(System.MONOCLINIC, "I2", 5),
    # Orthorhombic
    SpaceGroup(System.ORTHORHOMBIC, "P222", 16),
    SpaceGroup(System.ORTHORHOMBIC, "P2221", 17),
    SpaceGroup(System.ORTHORHOMBIC, "P2122", 17),
    SpaceGroup(System.ORTHORHOMBIC, "P2212", 17),
    SpaceGroup(System.ORTHORHOMBIC, "P21212", 18),
    SpaceGroup(System.ORTHORHOMBIC, "P22121", 18),
    SpaceGroup(System.ORTHORHOMBIC, "P21221", 18),
    SpaceGroup(System.ORTHORHOMBIC, "P212121", 19),
    SpaceGroup(System.ORTHORHOMBIC, "C2221", 20),
    SpaceGroup(System.ORTHORHOMBIC, "C222", 21),
    SpaceGroup(System.ORTHORHOMBIC, "F222", 22),
    SpaceGroup(System.ORTHORHOMBIC, "I222", 23),
    SpaceGroup(System.ORTHORHOMBIC, "I212121", 24),
    # Tetragonal
    SpaceGroup(System.TETRAGONAL, "P4", 75),
    SpaceGroup(System.TETRAGONAL, "P41", 76),
    SpaceGroup(System.TETRAGONAL, "P42", 77),
    SpaceGroup(System.TETRAGONAL, "P43", 78),
    SpaceGroup(System.TETRAGONAL, "I4", 79),
    SpaceGroup(System.TETRAGONAL, "I41", 80),
    SpaceGroup(System.TETRAGONAL, "P422", 89),
    SpaceGroup(System.TETRAGONAL, "P4212", 90),
    SpaceGroup(System.TETRAGONAL, "P4122", 91),
    SpaceGroup(System.TETRAGONAL, "P41212", 92),
    SpaceGroup(System.TETRAGONAL, "P4222", 93),
    SpaceGroup(System.TETRAGONAL, "P42212", 94),
    SpaceGroup(System.TETRAGONAL, "P4322", 95),
    SpaceGroup(System.TETRAGONAL, "P43212", 96),
    SpaceGroup(System.TETRAGONAL, "I422", 97),
    SpaceGroup(System.TETRAGONAL, "I4122", 98),
    # Trigonal
    SpaceGroup(System.TRIGONAL, "P3", 143),
    SpaceGroup(System.TRIGONAL, "P31", 144),
    SpaceGroup(System.TRIGONAL, "P32", 145),
    SpaceGroup(System.TRIGONAL, "P312", 149),
    SpaceGroup(System.TRIGONAL, "P321", 150),
    SpaceGroup(System.TRIGONAL, "P3112", 151),
    SpaceGroup(System.TRIGONAL, "P3121", 152),
    SpaceGroup(System.TRIGONAL, "P3212", 153),
    SpaceGroup(System.TRIGONAL, "P3221", 154),
    # Hexagonal
    SpaceGroup(System.HEXAGONAL, "P6", 168),
    SpaceGroup(System.HEXAGONAL, "P61", 169),
    SpaceGroup(System.HEXAGONAL, "P65", 170),
    SpaceGroup(System.HEXAGONAL, "P62", 171),
    SpaceGroup(System.HEXAGONAL, "P64", 172),
    SpaceGroup(System.HEXAGONAL, "P63", 173),
    SpaceGroup(System.HEXAGONAL, "P622", 177),
    SpaceGroup(System.HEXAGONAL, "P6122", 178),
    SpaceGroup(System.HEXAGONAL, "P6522", 179),
    SpaceGroup(System.HEXAGONAL, "P6222", 180),
    SpaceGroup(System.HEXAGONAL, "P6422", 181),
    SpaceGroup(System.HEXAGONAL, "P6322", 182),
    # Rhombohedral
    SpaceGroup(System.RHOMBOHEDRAL, "H3", 146),
    SpaceGroup(System.RHOMBOHEDRAL, "R3", 146),
    SpaceGroup(System.RHOMBOHEDRAL, "H32", 155),
    SpaceGroup(System.RHOMBOHEDRAL, "R32", 155),
    # Cubic
    SpaceGroup(System.CUBIC, "P23", 195),
    SpaceGroup(System.CUBIC, "F23", 196),
    SpaceGroup(System.CUBIC, "I23", 197),
    SpaceGroup(System.CUBIC, "P213", 198),
    SpaceGroup(System.CUBIC, "I213", 199),
    SpaceGroup(System.CUBIC, "P432", 207),
    SpaceGroup(System.CUBIC, "P4232", 208),
    SpaceGroup(System.CUBIC, "F432", 209),
    SpaceGroup(System.CUBIC, "F4132", 210),
    SpaceGroup(System.CUBIC, "I432", 211),
    SpaceGroup(System.CUBIC, "P4332", 212),
    SpaceGroup(System.CUBIC, "P4132", 213),
    SpaceGroup(System.CUBIC, "I4132", 214),
]


def space_group_to_db_format(space_group: SpaceGroup) -> str:
    """
    return space group encoded as 'hm[:ext]',
    i.e. format we use for storing space groups in project databases
    """
    name = space_group.hm  # type: ignore
    if space_group.ext != "\x00":  # type: ignore
        name += f":{space_group.ext}"  # type: ignore

    return name


def db_to_space_group(db_format: str) -> SpaceGroup:
    return gemmi.SpaceGroup(db_format)


def by_system():
    for system in System:
        yield list(filter(lambda sp: sp.system == system, SPACE_GROUPS))


def get_space_group(sg_short_name: str) -> Optional[SpaceGroup]:
    for space_group in SPACE_GROUPS:
        if space_group.short_name == sg_short_name:
            return space_group

    # no space groups with specified short name found
    return None
