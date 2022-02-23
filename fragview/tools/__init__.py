from typing import Optional, List
from enum import Enum, auto
from pathlib import Path
from gemmi import UnitCell
from dataclasses import dataclass
from importlib import import_module
from fragview.models import Fragment
from fragview.projects import Project
from fragview.space_groups import SpaceGroup
from fragview.sites.plugin import BatchFile


class UnknownToolNameException(Exception):
    pass


class Tool(Enum):
    # process tools
    DIALS = auto()
    XDS = auto()
    XDSAPP = auto()

    # refine tools
    DIMPLE = auto()
    FSPIPELINE = auto()

    # ligand fitting tools
    RHOFIT = auto()
    LIGANDFIT = auto()

    # ligand restrains tools
    GRADE = auto()
    ELBOW = auto()
    ACEDRG = auto()

    def get_name(self):
        return self.name.lower()


@dataclass
class ProcessOptions:
    space_group: Optional[SpaceGroup]
    cell: Optional[UnitCell]
    # currently unused, as there is no UI for this
    custom_args: str = ""
    # hard-coded to true, as there is no UI for this
    friedel_law: bool = True


@dataclass
class RefineOptions:
    pdb_file: Path
    # currently unused, as there is no UI for this
    custom_args: str = ""


@dataclass
class LigfitOptions:
    restrains_tool: Tool


def get_tool_by_name(name: str) -> Tool:
    for tool in Tool:
        if name == tool.name.lower():
            return tool

    raise UnknownToolNameException(name)


def _tool_plugin(tool: Tool):
    tool_module = import_module(f"fragview.tools.{tool.get_name()}")
    return tool_module


def generate_process_batch(
    tool: Tool, project: Project, dataset, options: ProcessOptions
) -> BatchFile:
    return _tool_plugin(tool).generate_batch(project, dataset, options)


def generate_refine_batch(
    tool: Tool,
    project: Project,
    dataset,
    proc_tool: str,
    input_mtz: Path,
    options: RefineOptions,
) -> BatchFile:
    return _tool_plugin(tool).generate_batch(
        project, dataset, proc_tool, input_mtz, options
    )


def generate_ligfit_batch(
    project: Project,
    tool: Tool,
    dataset,
    fragment: Fragment,
    proc_tool: str,
    refine_tool: str,
    result_dir: Path,
    options: LigfitOptions,
) -> BatchFile:
    return _tool_plugin(tool).generate_batch(
        project, dataset, fragment, proc_tool, refine_tool, result_dir, options
    )


def get_ligand_restrains_commands(tool: Tool, smiles: str, output: Path) -> List[str]:
    return _tool_plugin(tool).get_ligand_restrains_commands(smiles, output)
