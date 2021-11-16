from typing import Optional
from fragview.space_groups import SpaceGroup


def get_space_group_argument(space_group: Optional[SpaceGroup]) -> str:
    if space_group is None:
        # no (aka 'auto') space group specified
        return ""

    return f"xia2.settings.space_group={space_group.short_name}"
