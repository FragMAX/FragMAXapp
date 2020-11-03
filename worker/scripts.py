from os import path

UPDATE_STATUS_SCRIPT = "update_status.py"
PANDDA_WORKER = "pandda_prepare_runs.py"
UPDATE_RESULTS_SCRIPT = "update_results.py"


def update_status_path():
    """
    path to the update_status.py script
    """
    data_dir = path.join(path.dirname(__file__), "data")
    return path.join(data_dir, UPDATE_STATUS_SCRIPT)


def update_results_path():
    """
    path to the update_results.py script
    """
    data_dir = path.join(path.dirname(__file__), "data")
    return path.join(data_dir, UPDATE_RESULTS_SCRIPT)
