from fragview.projects import project_update_status_script, project_update_results_script


def scrsplit(a, n):
    k, m = divmod(len(a), n)
    lst = (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))
    return [x for x in lst if x]


def add_update_status_script_cmds(project, sample, batch, modules):
    dataset, run = sample.split("_")

    batch.load_python_env()
    batch.add_command(
        f"python3 {project_update_status_script(project)} {project.data_path()} {dataset} {run}")

    batch.purge_modules()
    batch.load_modules(modules)


def add_update_results_script_cmds(project, sample, batch, modules):

    batch.load_python_env()
    batch.add_command(
        f"python3 {project_update_results_script(project)} {sample} {project.proposal}/{project.shift}")

    batch.purge_modules()
    batch.load_modules(modules)
