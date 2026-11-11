"""EMG Signal Implementation."""
from .base import BaseSignal

class EMGSignal(BaseSignal):
    def get_signal_type(self) -> str: return "EMG"
    def get_typical_frequency_range(self) -> tuple: return (20.0, 500.0)
    def get_common_artifacts(self) -> list: return ["ECG", "motion", "powerline", "electrode_pop"]
    
    @classmethod
    def from_mne_raw(cls, raw):
        return cls(data=raw.get_data(), sfreq=raw.info['sfreq'], ch_names=raw.ch_names, ch_types=['emg']*len(raw.ch_names))
