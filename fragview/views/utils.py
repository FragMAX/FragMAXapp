import os
import stat


def scrsplit(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


def write_script(fname, contents):

    # make file executable by owner, read and writeable by group
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IWGRP

    try:
        # set umask that allow us to set all user and group access bits
        old_umask = os.umask(0o007)

        with os.fdopen(os.open(fname, os.O_CREAT | os.O_RDWR, mode), "w") as f:
            print(f"writing script file {fname}")
            f.write(contents)
    finally:
        # restore old umask
        os.umask(old_umask)


def Filter(datasetsList, filtersList):
    return [str for str in datasetsList if any(sub in str for sub in filtersList)]
