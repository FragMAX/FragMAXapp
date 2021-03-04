from unittest import IsolatedAsyncioTestCase
from jobs.jobsd import read_long_line, READ_CHUNK_SIZE


class EmulatedStreamReader:
    """
    simple emulation of asyncio's StreamReader
    """

    def __init__(self, data):
        self.data = data

    async def read(self, n):
        n = min(n, len(self.data))

        res = self.data[:n]
        self.data = self.data[n:]

        return res


class TestReadLongLine(IsolatedAsyncioTestCase):
    """
    test read_long_line() function
    """

    async def _test_reading(self, line):
        res = await read_long_line(EmulatedStreamReader(line))
        self.assertEqual(res, line)

    async def test_read_long_line(self):
        # test reading line that is slightly large then read chunk size
        long_line = b"x" * READ_CHUNK_SIZE + b"extra data\n"
        await self._test_reading(long_line)

        # check that reading short line works as well
        await self._test_reading(b"short line\n")
