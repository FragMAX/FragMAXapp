from fragview.views.utils import write_script
from fragview.projects import (
    project_script,
    project_update_status_script,
    project_raw_master_h5_files,
)
from fragview import hpc


def run_update_status(proj):
    body = """#!/bin/bash
#!/bin/bash
module purge
module load GCC/7.3.0-2.30  OpenMPI/3.1.1 Python/3.7.0
"""

    for h5 in project_raw_master_h5_files(proj):
        dataset, run = h5.split("/")[-1][:-10].split("_")
        body += f"python3 {project_update_status_script(proj)} {dataset}_{run} {proj.proposal}/{proj.shift}\n"

    script = project_script(proj, "update_status.sh")
    write_script(script, body)

    hpc.run_sbatch(script)
