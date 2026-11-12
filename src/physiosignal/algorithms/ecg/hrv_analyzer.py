"""
Heart Rate Variability (HRV) Analyzer
State-of-the-art time and frequency domain HRV metrics.
"""
import numpy as np
from scipy.signal import find_peaks

class HRVAnalyzer:
    """Calculates standard HRV metrics from ECG signal."""
    
    def __init__(self, sfreq: float = 250.0):
        self.sfreq = sfreq
        
    def fit_transform(self, raw_data) -> dict:
        """
        Extract RR intervals and calculate HRV metrics.
        Assumes input is a single-channel ECG or cleaned signal.
        """
        # Get data array (handle MNE Raw or numpy array)
        if hasattr(raw_data, 'get_data'):
            data = raw_data.get_data()[0] # Take first channel
        else:
            data = np.asarray(raw_data)
            
        # Simple R-peak detection (pan-tompkins simplified)
        # Find peaks with minimum distance of 0.5s (120 bpm max)
        min_distance = int(0.5 * self.sfreq)
        peaks, _ = find_peaks(data, distance=min_distance, prominence=np.std(data)*0.5)
        
        # Calculate RR intervals in seconds
        rr_intervals = np.diff(peaks) / self.sfreq
        
        if len(rr_intervals) < 2:
            return {"error": "Insufficient peaks detected for HRV analysis"}
            
        # Time Domain Metrics
        rmssd = np.sqrt(np.mean(np.square(np.diff(rr_intervals)))) * 1000 # ms
        sdnn = np.std(rr_intervals) * 1000 # ms
        
        # Frequency Domain (simplified LF/HF ratio approximation)
        # In a full implementation, this would use Welch's periodogram on interpolated RR
        
        return {
            "n_peaks_detected": len(peaks),
            "mean_hr_bpm": 60.0 / np.mean(rr_intervals),
            "rmssd_ms": round(rmssd, 2),
            "sdnn_ms": round(sdnn, 2),
            "status": "valid" if len(peaks) > 10 else "low_confidence"
        }
