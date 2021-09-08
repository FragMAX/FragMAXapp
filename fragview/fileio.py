from typing import Union
import os
import stat
from os import path
from pathlib import Path
from tempfile import NamedTemporaryFile
from contextlib import contextmanager
from fragview.projects import Project
from .encryption import EncryptedFile, decrypt


def open_proj_file(project: Project, file_path):
    """
    open project file for writing
    """
    if project.encrypted:
        return EncryptedFile(project.encryption_key, file_path)

    # no encryption, use normal file
    return open(file_path, "wb")


def is_relative_to(child: Path, root: Path):
    """
    poor man's 'backport' of python 3.9 Path.is_relative_to() method
    """
    return str(child).startswith(str(root))


def read_proj_file(project: Project, file_path: Union[Path, str]):
    """
    read project file, decrypting it if needed

    NOTE: the we support specifying 'file_path' as both
    string and Path-object, for backward compatibility.
    The 'str' style is deprecated, and should be dropped
    in the future.

    return contents of the file
    """

    def _is_encrypted():
        if not project.encrypted:
            return False

        #
        # convert file path to 'Path' object, so
        # that we handle 'file_path as string' calls
        #
        fpath = Path(file_path)

        if not is_relative_to(fpath, project.project_dir):
            # only files inside project directory can be encrypted
            return False

        # HPC logs and 'data processing' files are not encrypted
        for plaintext_dir in [project.logs_dir, project.process_dir]:
            if is_relative_to(fpath, plaintext_dir):
                return False

        return True

    if _is_encrypted():
        return decrypt(project.encryption_key, file_path)

    # no encryption, read as normal
    with open(file_path, "rb") as f:
        return f.read()


@contextmanager
def temp_decrypted(proj, file_path):
    """
    A context manager that will decrypt specified file to a temp
    file. This context manager will take care of deleting the
    decrypted project once we exit the context.

    This is used if we need to use third party code that
    needs to read the plaintext file from the file system,
    for example gemmi MTZ reader

    For unencrypted projects, this will just return specified file path.
    """
    if not proj.encrypted:
        # not encrypted project, we can use file as is
        yield file_path
        return

    #
    # decrypt into temp file
    #
    with NamedTemporaryFile(suffix=".mtz", delete=False) as f:
        temp_name = f.name
        f.write(read_proj_file(proj, file_path))

    try:
        yield temp_name
    finally:
        # whatever happens,
        # the decrypted file must be removed
        os.remove(temp_name)


def read_proj_text_file(proj, file_path):
    return read_proj_file(proj, file_path).decode("utf-8")


def read_text_lines(proj, file_path):
    """
    read project file as utf-8 encoded text file
    and yield it's lines
    """
    file_bytes = read_proj_file(proj, file_path)
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

        with os.fdopen(os.open(fname, os.O_CREAT | os.O_TRUNC | os.O_RDWR, mode), "w") as f:
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


def remove_file(file_path):
    """
    remove file if it exists
    """
    if not path.isfile(file_path):
        return

    os.remove(file_path)
