from typing import Optional
from importlib import import_module
from enum import Enum, auto
from fragview.space_groups import SpaceGroup


class Tools(Enum):
    DIALS = auto()
    XDS = auto()
    XDSAPP = auto()
    DIMPLE = auto()
    FSPIPELINE = auto()


def _tool_plugin(tool: Tools):
    tool_module = import_module(f"fragview.tools.{tool.name.lower()}")
    return tool_module


def get_space_group_argument(tool: Tools, space_group: Optional[SpaceGroup]) -> str:
    return _tool_plugin(tool).get_space_group_argument(space_group)
