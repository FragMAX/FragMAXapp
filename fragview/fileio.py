import os
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
