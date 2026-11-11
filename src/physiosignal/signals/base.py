"""Base Signal Interface. Universal interface for all physiological signal types."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np
import mne

class BaseSignal(ABC):
    def __init__(self, data: np.ndarray, sfreq: float, ch_names: list, ch_types: list):
        self.data = data
        self.sfreq = sfreq
        self.ch_names = ch_names
        self.ch_types = ch_types
        self.info = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types=ch_types)
        self.raw = mne.io.RawArray(data, self.info, verbose=False)
    
    @abstractmethod
    def get_signal_type(self) -> str: pass
    
    @abstractmethod
    def get_typical_frequency_range(self) -> tuple: pass
    
    @abstractmethod
    def get_common_artifacts(self) -> list: pass
    
    def to_mne_raw(self): return self.raw
    def get_duration(self) -> float: return self.data.shape[1] / self.sfreq
    def get_n_channels(self) -> int: return self.data.shape[0]
