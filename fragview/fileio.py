from .encryption import EncryptedFile


def open_proj_file(proj, file_path):
    """
    open project file for writing
    """
    if proj.encrypted:
        key = proj.encryptionkey.key
        return EncryptedFile(key, file_path)

    # no encryption, use normal file
    return open(file_path, "wb")
