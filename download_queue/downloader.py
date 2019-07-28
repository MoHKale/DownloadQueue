import os, typing, io
from threading import Thread
from abc import ABCMeta, abstractmethod
from requests import get as urlretrieve

from .decorators import repeat_on_error

DEFAULT_HEADERS = {
    # you almost always don't want who your downloading from to think you're a bot. If you disagree, pass headers={'User-Agent':None}
    'User-Agent': 'Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
}


class Downloader(Thread, metaclass=ABCMeta):
    def __init__(self, download_queue, **kwargs):
        """Downloader object which completes a network request
        concurrently and stores the response to a file like object.

        Parameters
        ----------
        download_queue : :obj:`download_queue.DownloadQueue`
            download queue instance from which thread was invoked.

        *args
            variable length argument list, any args specified here
            are supposed to be used by the overriding class to determine
            how best to download the src file. They shouldn't be passed
            back up the inheritance chain.
        **kwargs
            arbitrary keyword arguments. these are parsed in the
            constructor and have the following acceptable values:

                headers : :obj:`dict`
                params  : :obj:`dict`
                cookies : :obj:`dict`
                    attributes, sent on download request.
                session : :obj:`requests.Session`
                    if given all the above attributes are first
                    extracted from the session instance and then
                    overriden with the above arguments.
                completion_hook : Callable
                    function which will be called once download
                    has finished. function will be called with
                    the current downloader as its only argument.

                    NOTE if the download failed self.completed
                    will retain a Falsy value.
                block_on_error : :obj:`bool`
                    defaults to False. when true, if the attempted
                    download fails and raises an exception, that
                    exception will be allowed to gain top level
                    control of the running thread. This is almost
                    never what you'd want to happen.
                    from the file system.
        """
        super().__init__(target=self.download, daemon=True)

        self.queue = download_queue
        self.headers = DEFAULT_HEADERS.copy()
        self.params  = {}
        self.cookies = {}  # TODO keep as cookiejar

        if 'session' in kwargs:
            self._assign_params_from_session(kwargs.pop('session'))

        self.headers.update(kwargs.pop('headers', {}))
        self.headers.update(kwargs.pop('cookies', {}))
        self.params.update(kwargs.pop('params', {}))

        self.chunk_size       = kwargs.pop('chunk_size', 2 ** 10)  # default=1MB
        self.comhook          = kwargs.pop('completion_hook', None)
        self.block_on_error   = kwargs.pop('block_on_error', False)

        self.begin    = self.start
        self.complete = False

        if len(kwargs) > 0:  # unremoved keyword arguments exist
            raise ValueError("%s received unexpected keyword arguments: %s" % (
                self.__class__.__name__, ', '.join(kwargs.keys())
            ))

    def download(self):
        if self.complete:
            raise RuntimeError('downloader %s already completed' % hex(id(self)))

        self.logger.debug('attempting to download: %s' % (repr(self.serialise_args())[1:-1]))

        try:
            self._download()
        except (KeyboardInterrupt, Exception) as e: self._error_handler(e)
        else:                                       self._pass_handler()
        finally:
            if self.comhook: self.comhook(self)  # XXX code smell

    def _error_handler(self, e):
        if self.block_on_error:
            raise e  # reraise

    def _pass_handler(self):
        self.complete = True

    @property
    def logger(self): return self.queue.logger

    @abstractmethod
    def serialise_args(self):
        """primmed arguments list to be used by the logger should download fail"""
        pass

    @abstractmethod
    def _download(self):
        """actually downloads what the downloader is supposed to download"""
        pass

    def _assign_params_from_session(self, session):
        self.headers.update(session.headers)
        self.params.update(session.params)
        self.cookies.update(session.cookies.get_dict())


FileType = typing.Union[str, io.FileIO]


class GenericDownloader(Downloader):
    def __init__(self, download_queue,
                 link:                     str,
                 dest:                     FileType,
                 close_fd:                 bool = True,
                 delete_failed_fd:         bool = False,
                 overwrite_existing_files: bool = False,
                 **kwargs):
        """Generic Downloader to act as default for download_queue.
        This downloader attempts to provide a straightforward and
        customiseable means of downloading files through the download
        queue interface. It requires only two arguments, the url of
        the file being downloaded and the path where it is to be stored.
        If the given path isn't a string, its assumed to be writeable
        file like object, and that object is instead written to.

        Parameters
        ----------
        link
            url or session.get compatible argument which will be downloaded.
        dest
            file path to download to or file like object to write to.
        close_fd
            when truthy, if the download completes the file descriptor
            tied to this downloader will be automatically closed. Set
            this to false if you'd provide an io pseudo file object and
            would like to continue performing operations with it.
        delete_failed_fd
            when truthy and the download fails and the destination
            file descriptor has a name attribute, the file descriptor
            will be closed (regardless of `close_fd`) and the pointed
            to file will be deleted

            NOTE this option assumes close_fd=True
        overwrite_existing_files
            when a string is passed as destination (implying we need to
            open the file for writing) if the file already exists, it
            will be overwritten. This defaults to False.

        """
        self.link                      = link
        self.destination               = dest
        self._close_fd                 = close_fd
        self._delete_failed_fd         = delete_failed_fd
        self._overwrite_existing_files = overwrite_existing_files
        self._download_buffer          = io.BytesIO()
        self._download_buffer_complete = False

        # optional member attributes
        if 'attempt_count' in kwargs:    self.attempt_count    = kwargs.pop('attempt_count')
        if 'attempt_interval' in kwargs: self.attempt_interval = kwargs.pop('attempt_interval')

        super().__init__(download_queue, **kwargs)

    def __del__(self):
        self._download_buffer.close()

    @repeat_on_error(('attempt_count', 10), ('attempt_interval', 3))
    def _download(self):
        """read response into buffer and then dump to file, before closing"""
        if not self._download_buffer_complete:
            # downloaded data doesn't exist in memory yet.
            try:
                for chunk in self._iterate_response_chunks():
                    self._download_buffer.write(chunk)

                self._download_buffer_complete = True
            finally:
                # if succeeded, return to start for following write operation. If
                # failed, return to start so on next attempt, existing data in the
                # buffer is overwritten.
                self._download_buffer.seek(0)

        destination = self._get_dest_fd()

        # NOTE leave seek op here in case a previous write failed and some of the
        #      buffer was written, but some wasn't. it should have no performance
        #      cost if the file is at it's start position already.
        self._download_buffer.seek(0)

        destination.write(self._download_buffer.read())
        if self._close_fd:  # also flushes file
            destination.close()

    def _iterate_response_chunks(self):
        """make request and yield response chunks"""
        request_response = urlretrieve(self.link, headers=self.headers, cookies=self.cookies, stream=True)

        request_response.raise_for_status()  # only accept 200
        # TODO delegate request validation to caller

        for chunk in request_response.iter_content(self.chunk_size):
            if chunk: yield chunk  # generate valid chunks

    def _get_dest_fd(self):
        """get file like object to write to. Also repositions cursor at start of file"""
        if isinstance(self.destination, str):  # assume filepath
            if not self._overwrite_existing_files and os.path.exists(self.destination):
                raise FileExistsError(self.destination)

            self.destination = open(self.destination, 'wb')

        # assume file like object
        self.destination.seek(0)
        return self.destination

    def _error_handler(self, error):
        if self._delete_failed_fd and hasattr(self.destination, 'name'):
            name = self.destination.name
            self.destination.close()

            try:
                os.remove(name)
            except OSError: pass

        super()._error_handler(error)

    def serialise_args(self):
        return [self.link, self.destination.name if hasattr(self.destination, 'name') else self.destination]
