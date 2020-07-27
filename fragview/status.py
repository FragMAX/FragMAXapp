from fragview.views.utils import write_script
from fragview.projects import (
    project_script,
    project_scripts_dir,
    project_datasets,
    UPDATE_STATUS_SCRIPT,
)
from fragview import hpc


def run_update_status(proj):
    body = f"""#!/bin/bash
#!/bin/bash

module purge
module load GCC/7.3.0-2.30  OpenMPI/3.1.1 Python/3.7.0

cd {project_scripts_dir(proj)}

"""

    for dset in project_datasets(proj):
        dataset, run = dset.rsplit("_")
        body += f"python3 ./{UPDATE_STATUS_SCRIPT} {proj.data_path()} {dataset} {run}\n"

    script = project_script(proj, "update_status.sh")
    write_script(script, body)

    hpc.run_sbatch(script)
