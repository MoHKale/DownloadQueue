from .constants import *
from abc import ABC as AbstractClass
from abc import abstractproperty, abstractmethod
from time import sleep
from types import MethodType
from requests import get as urlretrieve
from traceback import print_tb as print_traceback
from datetime import datetime
## Create Upon Completion

class DownloadParent(object):
    def __init__(self, url, path, avoid_write_on_error=False): 
        self.url, self.path  = url, path
    
    @abstractmethod
    def download(self): 
        pass
        
    @abstractproperty
    def complete(self):
        pass
        
    @abstractproperty
    def failed(self):
        pass

class GenericDownload(DownloadParent):
    class Decorators(object):
        @staticmethod # Not callable as class method
        def delay_on_failure(interval):
            """Decorator To Delay Return Of Function Upon Download Failure"""
            def decorator(func):
                def wrapped(self, *args, **kwargs):
                    func(self, *args, **kwargs) # Do Function
                    if self.failed: sleep(interval)
                return wrapped
            return decorator
        
        @staticmethod # Not callable as class method
        def download_retry(attempt_count):
            """Decorator To Attempt Function This Many Times"""
            def decorator(func):
                def wrapped(self, *args, **kwargs):
                    for X in range(0, attempt_count):
                        func(self, *args, **kwargs) # Do Function
                        if not self.failed: break # End
                return wrapped
            return decorator
            
        @staticmethod
        def write_exception(file_path):
            def decorator(func):
                def wrapped(self, *args, **kwargs):
                    func(self, *args, **kwargs) # Do Function
                    
                    if self.failed and self._write_error is not None:
                        with open(file_path, 'a', encoding='utf8') as File:
                            File.write('Failed To Download "{0}" -> "{1}"\n\n'.format(
                                self.url, self.path # Format Download Arguments
                            ))
                            
                            File.write('Error Took Place At {0}\n\n'.format(datetime.now()))
                            print_traceback(self._download_error.__traceback__, file=File)
                            File.write(str(self._download_error)) # Because traceback lacks
                            File.write('-' * (len(self.url) + len(self.path) + 27) + '\n\n')
                return wrapped
            return decorator
        
    def __init__(self, url, path, **kwargs):
        self._chunk_size         = kwargs.pop('chunk_size', DEFAULT_CHUNK_SIZE)
        self._headers            = kwargs.pop('headers', HEADERS)
        self._cookies            = kwargs.pop('cookies', COOKIES)
        self._overwrite_existing = kwargs.pop('overwrite', True)
        self._write_error        = kwargs.pop('write_error', WRITE_ERROR_FILE_ON_FAILURE)
        
        #region Initial Non-Arg Variables
        self._download_begun = self._download_complete = False
        self._file_size      = self._downloaded_size   = None
        
        self._download_error = None # Exception container variable. Used to write file
        self._failed         = False # Variable indicating download Failed To Succeed
        #endregion
    
        super().__init__(url, path, **kwargs) # Call Parent Constructor
    
    @Decorators.download_retry(MINIMUM_ATTEMPT_COUNT)
    @Decorators.write_exception('DownloadError.error')
    @Decorators.delay_on_failure(DEFAULT_WAIT_ON_FAILURE)
    def download(self): # Actually Downloads
        try:
            if not self.complete:
                self._download_begun = True
                
                request_response = urlretrieve(
                    self.url, headers=self._headers, 
                    cookies=self._cookies, stream=True
                )
                
                request_response.raise_for_status() # Accept Only 200, otherwise raise
                
                self._file_size =  int(request_response.headers.get('Content-Length', 0))
                self._downloaded_size = 0 # Assign values to both file size and downloaded
                
                with open(self.path, 'wb') as local_file_instance:
                    for chunk in request_response.iter_content(self._chunk_size):
                        if not(chunk): continue # If some error in byte retrieval
                        
                        self._downloaded_size += len(chunk) # Increment chunk size
                        local_file_instance.write(chunk)   # Write byte to file
                        local_file_instance.flush()        # Clears file buffer
        except Exception as e: 
            self._failed, self._download_error = True, e
        else: 
            self._failed, self._download_complete = False, True
        
    def get_percentage(self):
        return 0 if self._file_size is None or self._downloaded_size is None else (
            self._downloaded_size / self._file_size if self._file_size != 0 else 0
        )
    
    @property
    def percentage(self):
        return self.get_percentage()
    
    @property
    def complete(self):
        return self._download_begun and self._download_complete
        
    @property
    def failed(self):
        return self._failed