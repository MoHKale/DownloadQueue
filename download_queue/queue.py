import warnings, logging, typing
from threading import BoundedSemaphore, RLock

from .downloader import GenericDownloader

LoggerOrTruthyType = typing.Union[None, bool, logging.Logger]

class DownloadQueue(object):
    """queue like data structure allowing concurrent downloading.

    This class provides the main interface to the DownloadQueue API. Whenever
    you wish to download something concurrently, simply pass your arguments to
    queue.add or queue.enqueue and the appropriate downloader will be instantiated
    and subsequently started. If the queue is full, the calling thread will be
    blocked until its request can be satisfied.

    This class also supports the context manager protocol, with the guarantee that
    on exit from the manager, all existing downloads will be completed.

    NOTE while being called a queue, this queue only supports addition operations.
         there is no dequeue method.

    Parameters
    ----------
    length
        the amount of concurrent downloads the queue is allowed to fascilitate.
    logger
        the logger to be used by this object. if it's a logging.Logger instance
        this thread will use it as it's sole logger. If otherwise it's a truthy
        value logging.getLogger(__name__) will be used and if its a falsy value
        the same logger will be used, however a null handler will be added.
    """
    def __init__(self, length: int = 5, logger: LoggerOrTruthyType = None):
        self.max_length, self.length = length, 0

        self._downloads_s = BoundedSemaphore(length)  # number of active downloads
        self._available_s = BoundedSemaphore(length)  # available slots in the queue

        for X in range(length): self._downloads_s.acquire(False)  # deplete bounded

        self._queue_lock = RLock()  # sync length modification operations

        if logger and isinstance(logger, logging.Logger):
            self.logger = logger
        else:
            self.logger = logging.getLogger(__name__)  # module logger
            if not logger: self.logger.addHandler(logging.NullHandler())

    def __del__(self,):
        with self._queue_lock:
            if self.length > 0:
                msg = "attempted to delete download queue at %s before all downloads finished" % (hex(id(self)))
                warnings.warn(msg, category=RuntimeWarning)  # give runtime warning on exit before download completion
                self.wait_until_finished()  # force exit to wait until download queue is complete and then finish

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.wait_until_finished()

    def add(self, *args, **kwargs):
        """begin a new download using the given args and kwargs.
        blocks when to many downloads are already taking place.

        See also: `download_queue.Downloader`

        Parameters
        ----------
        download_class
            the download_queue.Downloader like class which you is to be
            initialised and then begun
        """
        dclass  = kwargs.pop('download_class', GenericDownloader)
        dloader = dclass(self, *args, completion_hook=self._complete_handler, **kwargs)
        # NOTE init downloader before acquiring semaphore for it, because it could fail

        self._available_s.acquire()  # -1
        self._downloads_s.release()  # +1
        self._increment_length()

        dloader.begin()

    enqueue = add

    def _complete_handler(self, downloader):
        """invoke after a download thread is complete"""
        self._decrement_length()
        self._downloads_s.acquire(blocking=False)  # -1
        # don't block, because semaphore is only for use
        # in `DownloadQueue.wait_until_finished'.
        self._available_s.release()                # +1

    def wait_until_finished(self):
        """blocks the calling thread until all active downloads finish"""
        # NOTE acquire all the available slots in the queue, so that
        # the calling thread must wait until all the downloads are
        # complete and then release all slots immeadiately afterwards
        # WARN this assumes you aren't trying to add more downloads
        # while waiting for the existing downloads to finish.
        for X in range(self.max_length): self._available_s.acquire()
        for X in range(self.max_length): self._available_s.release()

    wait_to_finish = wait_until_finished

    def _increment_length(self):
        with self._queue_lock:
            self.length += 1

    def _decrement_length(self):
        with self._queue_lock:
            self.length -= 1

    @property
    def ready(self):
        return self.length < self.max_length

    @property
    def qlength(self): return self.max_length
