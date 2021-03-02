from fragview.dsets import parse_dataset_name
from fragview.projects import (
    project_script,
    project_scripts_dir,
    project_datasets,
    UPDATE_STATUS_SCRIPT,
)
from fragview.sites import SITE


def run_update_status(proj):
    hpc = SITE.get_hpc_runner()

    #
    # generate the wrapper batch script
    #
    script_file_path = project_script(proj, "update_status.sh")
    batch = hpc.new_batch_file(script_file_path)

    batch.load_python_env()
    batch.add_command(f"cd {project_scripts_dir(proj)}")

    for dset in project_datasets(proj):
        # for each dataset, run the update status script
        dataset, run = parse_dataset_name(dset)

        batch.add_command(
            f"python3 ./{UPDATE_STATUS_SCRIPT} {proj.data_path()} {dataset} {run}"
        )

    batch.save()

    #
    # invoke the wrapper batch script
    #
    hpc.run_batch(script_file_path)
