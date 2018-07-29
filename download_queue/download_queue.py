from .download import GenericDownload
from threading import Thread
from .exceptions import *

class DownloadThread(Thread):
    def __init__(self, dqueue, *args, **kwargs):
        super().__init__(
            target = self._target_method,
            args   = (args, kwargs),
            daemon = True
        )
        
        self.dqueue = dqueue
        
    def _target_method(self, args, kwargs):
        dc_instance = self.download_class(*args, **kwargs)
        dc_instance.download() # Begin Downloading Target
        
        self.dqueue.remove(self) # delete current thread
    
    download_class = GenericDownload


class OverflowQueue(object):
    """Queue To Store Overflowed Download Requests For Download Queue"""
    def __init__(self):
        self._queue = list()
        
    def __len__(self):
        return len(self._queue)

    def enqueue(self, item):
        self._queue.append(item)
        
    def dequeue(self):
        self._check_raise_empty() # Ensure !Empty
        return self._queue.pop(self.queue_pointer)
        
    def dequeue_or_none(self):
        return None if self.empty else self.dequeue
        
    def peek(self):
        self._check_raise_empty() # Ensure !Empty
        return self._queue[self.queue_pointer]
        
    def is_empty(self):
        return len(self) == 0
        
    @property
    def empty(self): return self.is_empty()

    @property
    def queue_pointer(self):
        return None if self.empty else len(self) - 1

    def _check_raise_empty(self):
        if self.empty: # When Empty Raise Exception
            raise OverflowQueueIsEmptyException()


class DownloadQueue(object):
    def __init__(self, queue_span, begin=True):
        self.length = queue_span # Maximum concurrent downloads allowed
        
        self._queue_contents = [] # List to store all current threads
        self._overflow_queue = OverflowQueue() # Infinite Length Queue
    
    def __len__(self): return self.length

    def add(self, *args, **kwargs):
        """Add download thread to queue for purposes"""
        download_thread = DownloadThread(self, *args, **kwargs)
        self._add_or_queue(download_thread) # Store thread
            
    def _add_or_queue(self, dt: DownloadThread):
        """Add to queue or store in overflow queue"""
        if self.ready: self._add(dt) # Add & Begin Download Thread
        else: self._overflow_queue.enqueue(dt) # Add To Overflow Queue
            
    def _add(self, dt: DownloadThread):
        """Actually Adds Thread To queue And Begins Download"""
        self._queue_contents.append(dt)
        dt.start() # Start Download Thread
        
    def _all_complete(self):
        return len(self._queue_contents) == 0 and len(self._overflow_queue) == 0 
        
    def _is_ready(self,):
        return len(self._queue_contents) != len(self)
        
    def remove(self, dt: DownloadThread):
        self._queue_contents.remove(dt)
        
        if not(self._overflow_queue.empty):
            self._add(self._overflow_queue.dequeue())
            
    def remove_index(self, index):
        self.remove(self._queue_contents[index])
    
    def wait_to_finish(self):
        while not(self._all_complete()):
            pass # Ignore
    
    @property
    def ready(self): return self._is_ready()
    
    
