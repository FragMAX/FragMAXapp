import os
import stat


def scrsplit(a, n):
    k, m = divmod(len(a), n)
    return (a[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(n))


def write_script(fname, contents):

    # make file executable by owner, read and writeable by group
    mode = stat.S_IRWXU | stat.S_IRGRP | stat.S_IWGRP

    with os.fdopen(os.open(fname, os.O_CREAT | os.O_RDWR, mode), "w") as f:
        print(f"writing script file {fname}")
        f.write(contents)
