from contextlib import contextmanager
import time
import redlock

# sleep time between attempts to aquire lock
POLL_TIMEOUT = 1.2


@contextmanager
def acquire(lock_id):
    lock = redlock.RedLock(lock_id)

    # loop until we acquire lock
    while not lock.acquire():
        time.sleep(POLL_TIMEOUT)

    # got lock, do the work
    yield

    # work done, release lock
    lock.release()
