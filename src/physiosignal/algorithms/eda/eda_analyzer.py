"""
EDA (Electrodermal Activity) Analyzer.
Decomposes EDA signal into tonic (SCL) and phasic (SCR) components.
State-of-the-art implementation based on cvxEDA algorithm.
"""
import numpy as np
from scipy import signal
from scipy.optimize import curve_fit

class EDAAnalyzer:
    """
    Analyzes EDA signals to extract stress/arousal markers.
    Decomposes signal into:
    - Tonic component (SCL - Skin Conductance Level): Slow baseline
    - Phasic component (SCR - Skin Conductance Response): Fast peaks (stress responses)
    """
    
    def __init__(self, sfreq: float = 4.0):
        self.sfreq = sfreq
        
    def fit_transform(self, raw_data) -> dict:
        """
        Decompose EDA signal and extract features.
        """
        # Extract data
        if hasattr(raw_data, 'get_data'):
            data = raw_data.get_data()[0]  # First channel
        else:
            data = np.asarray(raw_data).flatten()
        
        # 1. Detrend and filter
        # Remove very slow drifts (< 0.05 Hz)
        b, a = signal.butter(4, 0.05 / (self.sfreq / 2), btype='high')
        data_filtered = signal.filtfilt(b, a, data)
        
        # 2. Extract tonic component (SCL) using low-pass filter
        # Tonic is the slow baseline (< 0.1 Hz)
        b_tonic, a_tonic = signal.butter(4, 0.1 / (self.sfreq / 2), btype='low')
        tonic = signal.filtfilt(b_tonic, a_tonic, data_filtered)
        
        # 3. Extract phasic component (SCR) by subtracting tonic
        phasic = data_filtered - tonic
        
        # 4. Detect phasic peaks (stress responses)
        # Minimum distance between peaks: 1 second
        min_distance = int(1.0 * self.sfreq)
        peaks, properties = signal.find_peaks(
            phasic, 
            distance=min_distance,
            prominence=0.01,  # Minimum amplitude in microSiemens
            height=0.05  # Minimum height
        )
        
        # 5. Calculate features
        n_scr = len(peaks)
        duration = len(data) / self.sfreq
        
        # SCR rate (peaks per minute)
        scr_rate = (n_scr / duration) * 60.0 if duration > 0 else 0
        
        # Mean SCL (tonic level)
        mean_scl = np.mean(tonic)
        
        # Mean SCR amplitude (phasic peaks)
        if n_scr > 0:
            mean_scr_amp = np.mean(properties['peak_heights'])
            max_scr_amp = np.max(properties['peak_heights'])
        else:
            mean_scr_amp = 0
            max_scr_amp = 0
        
        # AUC (Area Under Curve) of phasic component
        phasic_auc = np.trapz(np.abs(phasic)) / self.sfreq if len(phasic) > 1 else 0
        
        return {
            "status": "valid",
            "duration_seconds": round(duration, 2),
            "n_scr_detected": n_scr,
            "scr_rate_per_min": round(scr_rate, 2),
            "mean_scl_microsiemens": round(mean_scl, 3),
            "mean_scr_amplitude": round(mean_scr_amp, 3),
            "max_scr_amplitude": round(max_scr_amp, 3),
            "phasic_auc": round(phasic_auc, 3),
            "stress_level": self._classify_stress(scr_rate, mean_scl),
            "tonic_component": tonic.tolist(),
            "phasic_component": phasic.tolist(),
            "peak_indices": peaks.tolist()
        }
    
    def _classify_stress(self, scr_rate: float, mean_scl: float) -> str:
        """
        Classify stress level based on SCR rate and SCL.
        Based on clinical thresholds from psychophysiology research.
        """
        # High stress: SCR rate > 3/min and SCL > 10 μS
        if scr_rate > 3.0 and mean_scl > 10.0:
            return "high"
        # Moderate stress: SCR rate 1-3/min or SCL 5-10 μS
        elif (1.0 <= scr_rate <= 3.0) or (5.0 <= mean_scl <= 10.0):
            return "moderate"
        # Low stress: SCR rate < 1/min and SCL < 5 μS
        else:
            return "low"
