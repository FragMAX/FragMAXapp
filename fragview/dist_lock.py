from contextlib import contextmanager
import time
import redlock
from redis import Redis
import conf


# sleep time between attempts to acquire lock
POLL_TIMEOUT = 1.2


def _redis_connection():
    return Redis.from_url(conf.REDIS_URL)


@contextmanager
def acquire(lock_id):
    lock = redlock.RedLock(lock_id, [_redis_connection()])

    # loop until we acquire lock
    while not lock.acquire():
        time.sleep(POLL_TIMEOUT)

    # got lock, do the work
    try:
        #
        # wrap yield inside try-finally block,
        # so that we release the lock even in the
        # case lock user code have raised an exception
        #
        yield
    finally:
        # work done, release lock
        lock.release()


def is_acquired(lock_id):
    """
    check if lock with specified ID is currently held
    """

    # check for the lock entry in the redis database,
    # not sure if this is a kosher way to do this, but
    # it seems to work
    return _redis_connection().get(lock_id) is not None
