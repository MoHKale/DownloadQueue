from abc import ABC as AbstractClass
from abc import abstractproperty, abstractmethod
from enum import IntEnum

class DownloadStatus(IntEnum):
    NotBegun    = 0
    Downloading = 1
    Complete    = 2
    Failed      = 3

    
class DownloadParent(AbstractClass):
    """Generic Class From Which All Downloaders Should Extend"""
    @abstractmethod
    def download(self):
        """Actually Performs The Dowload"""
        pass
        
    @abstractproperty
    def status(self) -> DownloadStatus:
        """Gives Download Related Information"""
        pass