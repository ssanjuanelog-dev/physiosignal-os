"""ECG Signal Implementation."""
from .base import BaseSignal

class ECGSignal(BaseSignal):
    def get_signal_type(self) -> str: return "ECG"
    def get_typical_frequency_range(self) -> tuple: return (0.5, 40.0)
    def get_common_artifacts(self) -> list: return ["baseline_wander", "muscle", "powerline"]
    
    @classmethod
    def from_mne_raw(cls, raw):
        return cls(data=raw.get_data(), sfreq=raw.info['sfreq'], ch_names=raw.ch_names, ch_types=['ecg']*len(raw.ch_names))
