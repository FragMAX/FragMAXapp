from os import path

UPDATE_STATUS_SCRIPT = "update_status.py"
PANDDA_WORKER = "pandda_prepare_runs.py"
READ_MTZ_FLAGS = "read_mtz_flags.py"


def read_mtz_flags_path():
    """
    path to the read_mtz_flags.py script
    """
    data_dir = path.join(path.dirname(__file__), "data")
    return path.join(data_dir, READ_MTZ_FLAGS)


def update_status_path():
    """
    path to the read_mtz_flags.py script
    """
    data_dir = path.join(path.dirname(__file__), "data")
    return path.join(data_dir, UPDATE_STATUS_SCRIPT)
