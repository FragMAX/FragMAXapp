import threading
from queue import Queue
from unittest import TestCase
from fragview.views.utils import start_thread


def _thread_func(queue: Queue):
    """
    function that is called from the 'start thread'

    will push current thread's ident and daemon flag to the
    provided queue

    this way we can test arguments passing and pass back info
    about the started thread
    """
    our_thread = threading.current_thread()
    queue.put((our_thread.ident, our_thread.daemon))


class TestStartThread(TestCase):
    def test_start_thread(self):

        # start new thread, use queue to
        # receive data on started thread
        queue = Queue(1)
        start_thread(_thread_func, queue)
        ident, daemon = queue.get()

        # check that _thread_func() was run in a different thread
        main_thread = threading.current_thread()
        self.assertNotEqual(main_thread.ident, ident)
        # check that new thread was daemonic
        self.assertTrue(daemon)
