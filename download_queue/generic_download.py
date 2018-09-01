from .download import DownloadStatus, DownloadParent

from requests import get as urlretrieve

from .constants import (
    DEFAULT_CHUNK_SIZE, 
    HEADERS, COOKIES,
    MINIMUM_ATTEMPT_COUNT,
    DEFAULT_WAIT_ON_FAILURE
)

from functools import wraps
from time import sleep
from datetime import datetime

class UnknownKeywordArgumentsGivenException(Exception):
    pass


class Decorators(object):
    def try_upto_x_times(attempt_count):
        """Runs a function upto X times until no exception is discovered"""
        def decorator(func):
            @wraps(func)
            def wrapped(*args, **kwargs):
                for X in range(0, attempt_count):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if X == attempt_count - 1:
                            raise e # re raise on last 
            return wrapped
        return decorator
    
    def delay_exception(time_interval):
        """Runs a function, if an exception is reached, the execution
        of the exception is delayed by this interval before continuing"""
        def decorator(func):
            @wraps(func)
            def wrapped(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except KeyboardInterrupt: pass
                except Exception as e:
                    sleep(time_interval)
                    raise e # re raise 
            return wrapped
        return decorator
        
    def mark_status_as_failure(func):
        """If an exception is raised by the callable function,
        the generic download instance status is set to failed"""
        @wraps(func)
        def wrapped(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except (KeyboardInterrupt, Exception) as e:
                self.status = DownloadStatus.Failed
                raise e # re raise to top stack
        return wrapped


class GenericDownload(DownloadParent):
    """Simplified Generic Download Class To Simplify Downloading
    """
    def __init__(self, url, path, **kwargs):
        self._chunk_size         = kwargs.pop('chunk_size', DEFAULT_CHUNK_SIZE)
        self._headers            = kwargs.pop('headers', HEADERS)
        self._cookies            = kwargs.pop('cookies', COOKIES)
        self._overwrite_existing = kwargs.pop('overwrite', True)
        self.url, self.path      = url, path # store locally
        self.status              = DownloadStatus.NotBegun
        
        if len(kwargs) != 0: # Any unremoved keyword arguments
            raise UnknownKeywordArgumentsGivenException(kwargs)

    @Decorators.mark_status_as_failure
    @Decorators.try_upto_x_times(MINIMUM_ATTEMPT_COUNT)
    @Decorators.delay_exception(DEFAULT_WAIT_ON_FAILURE)
    def download(self):
        if self.status == DownloadStatus.Downloading:
            return # Begun on seperate thread
        
        self.status = DownloadStatus.Downloading # Assign
        
        with open(self.path, 'wb') as local_file_instance:
            for chunk in self._iterate_response_chunks(self.url):
                local_file_instance.write(chunk) # Write byte to file
                local_file_instance.flush() # Clears file buffer
        
        self.status = DownloadStatus.Complete
        
    def _iterate_response_chunks(self, url):
        request_response = urlretrieve(
            url, headers=self._headers, 
            cookies=self._cookies, stream=True
        )
        
        request_response.raise_for_status() # Accept Only 200
        
        for chunk in request_response.iter_content(self._chunk_size):
            if not(chunk): continue 
            yield chunk # When Response Chunk Is Valid
    
    #region Abstract Property Assignments
    @property
    def status(self): return self._status
        
    @status.setter
    def status(self, value): self._status = value
    #endregion
