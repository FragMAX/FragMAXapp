from contextlib import contextmanager
import time
import redis
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


def is_acquired(lock_id):
    """
    check if lock with specified ID is currently held
    """

    # check for the lock entry in the redis database,
    # not sure if this is a kosher way to do this, but
    # it seems to work
    r = redis.Redis()
    return r.get(lock_id) is not None
