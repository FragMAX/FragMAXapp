import json
from sys import stdout
from pathlib import Path
from shutil import copyfile, copytree
from dataclasses import dataclass
from pandas import read_csv
from django.core.management.base import BaseCommand, CommandError
from fragview.models import UserProject
from fragview.crystals import Crystals, Crystal
from fragview.projects import Project, get_project
from fragview.scraper import REFINE_TOOLS, LIGFIT_TOOLS
from fragview.status import (
    update_proc_tool_status,
    update_refine_tool_status,
    update_ligfit_tool_status,
)
from projects.database import db_session
from worker.project import setup_project


@dataclass
class OldPaths:
    fragmax_dir: Path
    process_dir: Path
    results_dir: Path
    models_dir: Path
    pandda_dir: Path
    datacollections_csv: Path


def _log(msg):
    print(msg)
    stdout.flush()


def _check_dir(path: Path):
    if not path.is_dir():
        raise CommandError(f"No such directory: '{path}'")


def _check_file(path: Path):
    if not path.is_file():
        raise CommandError(f"No such file: '{path}'")


def _get_old_paths(protein, proposal, shift) -> OldPaths:
    fragmax_dir = Path("/data/visitors/biomax", proposal, shift, "fragmax")
    _check_dir(fragmax_dir)

    process_dir = Path(fragmax_dir, "process", protein)
    _check_dir(process_dir)

    results_dir = Path(fragmax_dir, "results")
    _check_dir(results_dir)

    models_dir = Path(fragmax_dir, "models")
    _check_dir(models_dir)

    pandda_dir = Path(results_dir, "pandda", protein)
    # don't check if pandda dir exists,
    # as a project maybe lacking pandda dir, if not pandda
    # processing have been performed

    datacollections_csv = Path(process_dir, "datacollections.csv")
    _check_file(datacollections_csv)

    return OldPaths(
        fragmax_dir,
        process_dir,
        results_dir,
        models_dir,
        pandda_dir,
        datacollections_csv,
    )


def _parse_datacollections_csv(datacollections_csv: Path) -> Crystals:
    def _gen_crystals():
        csv = read_csv(datacollections_csv)

        sample_ids = set()
        for line_num, row in csv.iterrows():
            sample_ids.add(row.imagePrefix)

        for sample_id in sample_ids:
            _, frag_lib, frag_code = sample_id.split("-")

            #
            # currently, we only support migrating 'F2XUniversal' projects
            #
            assert frag_lib == "F2XUniversal"

            # chop off the 'subwell' part, to get proper fragment code
            frag_code = frag_code[:-1]

            _log(f"{sample_id=} {frag_lib=} {frag_code=}")

            if frag_code.lower().startswith("apo"):
                frag_lib = None
                frag_code = None

            yield Crystal(
                SampleID=sample_id, FragmentLibrary=frag_lib, FragmentCode=frag_code
            )

    return Crystals(list(_gen_crystals()))


def _create_project(protein: str, proposal: str, crystals: Crystals) -> Project:
    user_proj = UserProject.create_new(protein, proposal)
    project_id = user_proj.id
    setup_project(project_id, protein, proposal, crystals.as_list(), False, False)

    return get_project(project_id)


def _import_models(project: Project, old_paths: OldPaths):
    _log("IMPORT MODELS")
    for node in old_paths.models_dir.iterdir():
        if not node.is_file():
            continue

        if not node.name.lower().endswith(".pdb"):
            continue

        dest = Path(project.models_dir, node.name)
        _log(f"{node} -> {dest}")
        copyfile(node, dest)
        project.db.PDB(filename=node.name)


def _dbg_cutoff(dsets):
    return dsets
    # from itertools import islice
    #
    # return islice(dsets, 0, 14)


def _migrate_proc_tool(project: Project, old_paths: OldPaths, tool: str):
    _log(f"MIGRATE PROC TOOL {tool} RESULTS")
    tool_dir = "xdsxscale" if tool == "xds" else tool

    for dset in _dbg_cutoff(project.get_datasets()):
        src_dir = Path(old_paths.process_dir, dset.crystal.id, dset.name, tool_dir)
        if not src_dir.is_dir():
            # no tool results found for this dataset
            continue

        dest_dir = Path(project.get_dataset_process_dir(dset), tool)
        _log(f"{src_dir} -> {dest_dir}")
        _copytree(src_dir, dest_dir)
        update_proc_tool_status(project, tool, dset)


def _maybe_resync_ligfit_tool(project, tool, dset):
    _log(f"maybe resync {project=}, {tool=}, {dset=}")
    res_dir = project.get_dataset_results_dir(dset)

    if tool == "ligandfit":
        ligfit_dir = "ligfit"
    else:
        assert tool == "rhofit"
        ligfit_dir = "rhofit"

    if not next(res_dir.glob(f"*/*/{ligfit_dir}"), None):
        return

    update_ligfit_tool_status(project, tool, dset)


def _copytree(src_dir, dest_dir):
    def _ignore(dir, nodes):
        # filter out broken symlinks
        def _f():
            for node in nodes:
                p = Path(dir, node)
                if p.is_symlink() and not p.exists():
                    # broken symlink, ignore it
                    _log(f"ignoring broken link {dir=} {node=}")
                    yield node

        return list(_f())

    copytree(src_dir, dest_dir, ignore=_ignore)


def _migrate_refine(project: Project, old_paths: OldPaths):
    _log("MIGRATE REFINE RESULTS")
    for dset in _dbg_cutoff(project.get_datasets()):
        for proc_tool in ["xds", "xdsapp", "dials"]:
            proc_dir = "xdsxscale" if proc_tool == "xds" else proc_tool
            src_dir = Path(old_paths.results_dir, dset.name, proc_dir)
            if not src_dir.is_dir():
                # no tool results found for this dataset
                continue

            dest_dir = Path(project.get_dataset_results_dir(dset), proc_tool)
            _log(f"{src_dir} -> {dest_dir}")
            # note, we can't use ignore_dangling_symlinks=True
            # here due to https://bugs.python.org/issue38523
            _copytree(src_dir, dest_dir)

        for tool in REFINE_TOOLS:
            update_refine_tool_status(project, tool, dset)

        for tool in LIGFIT_TOOLS:
            _maybe_resync_ligfit_tool(project, tool, dset)


def _migrate_pandda(project: Project, old_paths: OldPaths):
    def _migrate_pandda_selection_json(selection_json: Path):
        if not selection_json.is_file():
            _log(f"{selection_json} does not exist, will not try to migrate it")
            return

        _log(f"upgrading {selection_json} format")

        with Path(selection_json).open("r") as f:
            old = json.load(f)

        new = []
        for dset, pdb in old.items():
            new.append([dset, pdb])

        with Path(selection_json).open("wt") as f:
            json.dump(new, f, indent=True)

    _log("MIGRADE PANDDA")

    if not old_paths.pandda_dir.is_dir():
        _log("No pandda results found, will not migrate PanDDa")
        return

    for src in old_paths.pandda_dir.glob("*_*"):
        if not src.is_dir():
            continue

        dest = Path(project.pandda_dir, src.name)
        _log(f"{src} -> {dest}")
        _copytree(src, dest)
        _migrate_pandda_selection_json(Path(dest, "selection.json"))


class Command(BaseCommand):
    help = "Import old project"

    def add_arguments(self, parser):
        parser.add_argument("protein", type=str)
        parser.add_argument("proposal", type=str)
        parser.add_argument("shift", type=str)

    @db_session
    def _handle(self, *args, **options):
        protein = options["protein"]
        proposal = options["proposal"]
        shift = options["shift"]
        old_paths = _get_old_paths(protein, proposal, shift)
        project = get_project("8")

        _migrate_pandda(project, old_paths)

    def handle(self, *args, **options):
        protein = options["protein"]
        proposal = options["proposal"]
        shift = options["shift"]

        old_paths = _get_old_paths(protein, proposal, shift)
        crystals = _parse_datacollections_csv(old_paths.datacollections_csv)

        project = _create_project(protein, proposal, crystals)
        with db_session:
            _import_models(project, old_paths)
            _migrate_proc_tool(project, old_paths, "xds")
            _migrate_proc_tool(project, old_paths, "xdsapp")
            _migrate_proc_tool(project, old_paths, "dials")
            _migrate_refine(project, old_paths)
            _migrate_pandda(project, old_paths)
