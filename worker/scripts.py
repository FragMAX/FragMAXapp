from os import path

READ_MTZ_FLAGS = "read_mtz_flags.py"


def read_mtz_flags_path():
    """
    path to the read_mtz_flags.py script
    """
    data_dir = path.join(path.dirname(__file__), "data")
    return path.join(data_dir, READ_MTZ_FLAGS)
