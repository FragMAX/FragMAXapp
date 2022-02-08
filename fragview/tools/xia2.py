from typing import Optional
from gemmi import UnitCell
from fragview.space_groups import SpaceGroup


def get_space_group_argument(space_group: Optional[SpaceGroup]) -> str:
    if space_group is None:
        # no (aka 'auto') space group specified
        return ""

    return f"xia2.settings.space_group={space_group.short_name}"


def get_cell_argument(cell: Optional[UnitCell]) -> str:
    if cell is None:
        # no (aka 'auto') cell parameters specified
        return ""

    return (
        f"unit_cell={cell.a}, {cell.b}, {cell.c}, "
        f"{cell.alpha}, {cell.beta}, {cell.gamma}"
    )


def get_friedel_argument(friedel_law: bool):
    if friedel_law:
        return "atom=X"

    return ""
