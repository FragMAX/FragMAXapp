from pathlib import Path
from struct import pack, unpack


class JobIDs:
    """
    keep track of Job IDs sequence

    the next available ID is stored on disk,
    which allows to continue job IDs sequence
    after jobsd restart
    """

    NEXT_ID_FORMAT = "!L"

    def __init__(self, persistence_dir):
        """
        persistence_dir - directory where to job IDs persistence data file is stored
        """
        self._next_id_file = Path(persistence_dir, "jobsd.data")
        self._next_id = self._get_stored_next_id()

    def _get_stored_next_id(self):
        if not self._next_id_file.is_file():
            # no stored IDs found, start from the beginning
            return 1

        # load next job ID from the file
        (res,) = unpack(self.NEXT_ID_FORMAT, self._next_id_file.read_bytes())

        return res

    def next(self):
        res = self._next_id

        # calculate new next ID and
        # store it on disk
        self._next_id += 1
        self._next_id_file.write_bytes(pack(self.NEXT_ID_FORMAT, self._next_id))

        return str(res)
