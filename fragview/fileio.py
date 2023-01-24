from typing import Union
import os
import stat
from pathlib import Path
from fragview.projects import Project


def open_proj_file(project: Project, file_path):
    """
    open project file for writing
    """
    return open(file_path, "wb")


def read_proj_file(file_path: Union[Path, str]):
    """
    read project file

    NOTE: that we support specifying 'file_path' as both
    string and Path-object, for backward compatibility.
    The 'str' style is deprecated, and should be dropped
    in the future.

    return contents of the file
    """
    with open(file_path, "rb") as f:
        return f.read()


def read_proj_text_file(proj, file_path):
    return read_proj_file(file_path).decode("utf-8")


def read_text_lines(proj, file_path):
    """
    read project file as utf-8 encoded text file
    and yield it's lines
    """
    file_bytes = read_proj_file(file_path)
    for line in file_bytes.decode("utf-8").splitlines():
        yield line


def makedirs(dir_path):
    """
    basically 'mkdir -p', but also set access mode to make
    the directory readable, writable and executable for owner and the group
    """
    os.makedirs(dir_path, mode=0o770, exist_ok=True)


def write_script(fname, contents):

    # make file executable by owner, read and writeable by group
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP

    try:
        # set umask that allow us to set all user and group access bits
        old_umask = os.umask(0o007)

        with os.fdopen(
            os.open(fname, os.O_CREAT | os.O_TRUNC | os.O_RDWR, mode), "w"
        ) as f:
            print(f"writing script file {fname}")
            f.write(contents)
    finally:
        # restore old umask
        os.umask(old_umask)


def subdirs(root_dir, depth):
    """
    list subdirectories exactly at the specified depth
    """

    def _iterdirs(root_dir):
        for chld in root_dir.iterdir():
            if chld.is_dir():
                yield chld

    if not root_dir.is_dir():
        return

    if depth == 1:
        for chld in _iterdirs(root_dir):
            yield chld

        return

    sublevel = depth - 1
    for chld in _iterdirs(root_dir):
        for sub in subdirs(chld, sublevel):
            yield sub


def upload_dir(src_dir, res_dir):
    return f"mkdir -p {res_dir}\nrsync --recursive --delete {src_dir}/* {res_dir}\n"
