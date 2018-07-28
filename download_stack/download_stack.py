from .download import GenericDownload
from threading import Thread
from .exceptions.stack import *

class DownloadThread(Thread):
    def __init__(self, dstack, *args, **kwargs):
        super().__init__(
            target = self._target_method,
            args   = (args, kwargs),
            daemon = True
        )
        
    def _target_method(self, args, kwargs):
        dc_instance = self.download_class(*args, **kwargs)
        dc_instance.download() # Begin Downloading Target
        
        self.dstack.remove(self) # delete current thread
    
    download_class = GenericDownload


class OverflowQueue(object):
    """Queue To Store Overflowed Download Requests For Download Stack"""
    def __init__(self):
        self._queue = list()
        
    def __len__(self):
        return len(self._queue)

    def enqueue(self, item):
        self._queue.append(item)
        
    def dequeue(self):
        self._check_raise_empty() # Ensure !Empty
        return self._queue.pop(self.stack_pointer)
        
    def dequeue_or_none(self):
        return None if self.empty else self.dequeue
        
    def peek(self):
        self._check_raise_empty() # Ensure !Empty
        return self._queue[self.stack_pointer]
        
    def is_empty(self):
        return len(self) == 0
        
    @property
    def empty(self): return self.is_empty()

    @property
    def stack_pointer(self):
        return None if self.empty else len(self) - 1

    def _check_raise_empty(self):
        if self.empty: # When Empty Raise Exception
            raise OverflowQueueIsEmptyException()


class DownloadStack(object):
    def __init__(self, stack_span, begin=True):
        #super().__init__(target=self._stack_loop, daemon=True)
        
        self.length = stack_span
        
        self._stack_contents = [] # List to store all current threads
        self._overflow_queue = OverflowQueue() # Infinite Length Queue
        #self.running         = False # Whether thread/stack is running
    
    def __len__(self): return self.length

    def add(self, *args, **kwargs):
        """Add download thread to stack for purposes"""
        download_thread = DownloadThread(self, *args, **kwargs)
        self._add_or_queue(download_thread) # Store thread
            
    def _add_or_queue(self, dt: DownloadThread):
        """Add to stack or store in overflow queue"""
        if self.ready: self._add(dt) # Add & Begin Download Thread
        else: self._overflow_queue.enqueue(dt) # Add To Overflow Queue
            
    def _add(self, dt: DownloadThread):
        """Actually Adds Thread To Stack And Begins Download"""
        self._stack_contents.append(dt)
        dt.start() # Start Download Thread
        
    def _all_complete(self):
        return len(self._stack_contents) > 0 or len(self._overflow_queue) > 0 
        
    def _is_ready(self,):
        return len(self._stack_contents) != len(self)
        
    def remove(self, dt: DownloadThread):
        self._stack_contents.remove(dt)
        
        if not(self._overflow_queue.empty):
            self._add(self._overflow_queue.dequeue())
        
    def remove_index(self, index):
        self.remove(self._stack_contents[index])
    
    def wait_to_finish(self):
        while not(self._all_complete):
            pass # Ignore
    
    @property
    def ready(self): return self._is_ready()
    
















































