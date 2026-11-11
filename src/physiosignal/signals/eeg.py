"""EEG Signal Implementation."""
from .base import BaseSignal

class EEGSignal(BaseSignal):
    def get_signal_type(self) -> str: return "EEG"
    def get_typical_frequency_range(self) -> tuple: return (0.5, 100.0)
    def get_common_artifacts(self) -> list: return ["blinks", "eye_movements", "muscle", "line_noise"]
    
    @classmethod
    def from_mne_raw(cls, raw):
        return cls(data=raw.get_data(), sfreq=raw.info['sfreq'], ch_names=raw.ch_names, ch_types=['eeg']*len(raw.ch_names))
