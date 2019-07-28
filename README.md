# DownloadQueue
facilities for Thread based concurrent downloading

## NOTE
if you intend to make a lot (**LOT**) of downloads simultaneously, you might find better results with [subprocesses](https://docs.python.org/3.8/library/multiprocessing.html#multiprocessing.pool.Pool). Pythons usage of a GIL renders multithreading to be more of an IO bound solution, where as subprocesses are a processing bound solution.

I developed this module, because I found signal handling and keyboard interrupts with subprocesses to be much harder to reasonably control than they're with threads.

## Overview
This module is implemented in two parts. First there's the queue which manages the amount of concurrently tolerated downloads and gives ways to both add new downloads &amp; pause execution while waiting for downloads to finish. The second part is downloaders; objects which extend from thread and provide the fascilities to actually download files. You can see the main queue implementation [here](./download_queue/queue.py) and the downloader base class + the generic/default implementation [here](./download_queue/downloader.py).

### Examples
The following examples all assume you've imported download_queue.DownloadQueue as follows `from download_queue import DownloadQueue`.

DownloadQueue takes two arguments, length and logger. You can see more info about logger in the documentation, for now all we're concerned with is length. The length parameter specifies how many files the queue is allowed to download at once. The default is 5.

```python
queue = DownloadQueue(3)

queue.add(url1, fd1)
queue.add(url2, fd2)
queue.add(url3, fd3)

# will be blocked until above complete
queue.add(url4, fd4)
```

When the queue is disposed, the exit thread will be blocked until all the downloads complete and a runtime warning will be issued. To prevent this, please call `queue.wait_until_finished()` before terminating the program. This'll let the downloads continue happening concurrently, however will force the calling thread to wait until they're **all** complete before returning.

```python
queue = DownloadQueue(3)

queue.add(url1, fd1)
queue.add(url2, fd2)
queue.add(url3, fd3)

queue.wait_until_finished()
```

DownloadQueue also supports the context manager protocol, allowing you to rewrite the above example in a more succinct manner.

```python
with DownloadQueue(3) as queue:
    queue.add(url1, fd1)
    queue.add(url2, fd2)
    queue.add(url3, fd3)
```

you can also specify some general request arguments to be made while attempting the download. Including request headers, cookies, chunk sizes etc. For a list of them, see [downloader.py](./download_queue/downloader.py).
