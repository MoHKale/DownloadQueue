import unittest, io, requests, traceback
from hashlib import sha256
from download_queue import GenericDownloader, DownloadQueue

class TestGenericDownloader(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def make_download_target(url, hash):
            return {'url': url, 'hash': hash}

        cls.valid_download_target = make_download_target(
            'https://www.google.co.uk/images/branding/googlelogo/1x/googlelogo_color_272x92dp.png',
            '5776cd87617eacec3bc00ebcf530d1924026033eda852f706c1a675a98915826'
        )
        cls.invalid_download_target = 'http://google.co.uk/404'

    def _hash_bytes_io(self, bytes_io):
        m = sha256()
        m.update(bytes_io.read())
        return m.hexdigest()

    def test_downloader_can_download(self):
        url, hash = self.valid_download_target.values()

        destination = io.BytesIO()
        downloader  = GenericDownloader(None, url, destination, close_fd=False)
        downloader._download()
        destination.seek(0)  # revert point to start of file

        self.assertEqual(hash, self._hash_bytes_io(destination))

    def test_downloader_tries_enough_times_on_failure(self):
        url, attempt_count, exc = self.invalid_download_target, 3, None
        queue = DownloadQueue()

        destination = io.BytesIO()
        downloader  = GenericDownloader(queue, url, destination, attempt_interval=0, attempt_count=attempt_count)

        try:
            downloader._download()
        except requests.RequestException as e: exc = e
        else:                                  exc = None

        if not exc: self.fail('request to invalid download target didn\'t raise an exception: %s' % url)

        tb_list = list(traceback.TracebackException.from_exception(exc).format())
        err_msg = tb_list[-1]

        exc_count = len([X for X in tb_list if X == err_msg])
        self.assertEqual(attempt_count, exc_count)
