from pathlib import Path
from fragview.projects import Project, project_log_path, project_script
from fragview.tools import LigfitOptions, get_ligand_restrains_commands
from fragview.models import Fragment
from fragview.sites.plugin import BatchFile, Duration
from fragview.sites.current import get_hpc_runner
from fragview.versions import BUSTER_MOD, PHENIX_MOD

PRESTO_MODULES = ["gopresto", BUSTER_MOD, PHENIX_MOD]


def generate_batch(
    project: Project,
    dataset,
    fragment: Fragment,
    proc_tool: str,
    refine_tool: str,
    result_dir: Path,
    options: LigfitOptions,
) -> BatchFile:

    script_prefix = f"rhofit-{proc_tool}-{refine_tool}-{dataset.name}"
    batch = get_hpc_runner().new_batch_file(
        "RhoFit",
        project_script(project, f"{script_prefix}.sh"),
        project_log_path(project, f"{script_prefix}_%j_out.txt"),
        project_log_path(project, f"{script_prefix}_%j_err.txt"),
        cpus=1,
    )
    batch.set_options(time=Duration(hours=1))

    batch.purge_modules()
    batch.load_modules(PRESTO_MODULES)

    restrains_output = Path(result_dir, fragment.code)
    restrains_cmds = get_ligand_restrains_commands(
        options.restrains_tool, fragment.smiles, restrains_output
    )

    outdir = Path(result_dir, "rhofit")
    mtz_input = Path(result_dir, "final.mtz")
    pdb = Path(result_dir, "final.pdb")

    batch.add_commands(
        *restrains_cmds,
        f"rm -rf {outdir}",
        f"rhofit -l {restrains_output}.cif -m {mtz_input} -p {pdb} -d {outdir}",
    )

    return batch
