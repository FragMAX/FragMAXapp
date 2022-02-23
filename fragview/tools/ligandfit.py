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

    script_prefix = f"ligandfit-{proc_tool}-{refine_tool}-{dataset.name}"
    batch = get_hpc_runner().new_batch_file(
        "LigandFit",
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

    outdir = Path(result_dir, "ligfit")
    mtz_input = Path(result_dir, "final.mtz")
    model_pdb = Path(result_dir, "final.pdb")
    ligand_cif = f"{restrains_output}.cif"

    batch.add_commands(
        *restrains_cmds,
        f"rm -rf {outdir}",
        f"mkdir -p {outdir}",
        f"cd {outdir}",
        f"phenix.ligandfit data={mtz_input} model={model_pdb} "
        f"ligand={ligand_cif} fill=True clean_up=True",
    )

    return batch
