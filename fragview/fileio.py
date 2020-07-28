import os
import stat
from .encryption import EncryptedFile, decrypt


def open_proj_file(proj, file_path):
    """
    open project file for writing
    """
    if proj.encrypted:
        key = proj.encryptionkey.key
        return EncryptedFile(key, file_path)

    # no encryption, use normal file
    return open(file_path, "wb")


def read_proj_file(proj, file_path):
    """
    read project file, decrypting it if needed

    return contents of the file
    """
    if proj.encrypted:
        return decrypt(proj.encryptionkey.key, file_path)

    # no encryption, read as normal
    with open(file_path, "rb") as f:
        return f.read()


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
