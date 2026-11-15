"""
EEG Welch Power Spectral Density (PSD) Analyzer.
Calculates absolute and relative band powers for standard EEG frequency bands.
"""
import numpy as np
from scipy import signal

# Compatibility for NumPy < 2.0 and >= 2.0
if hasattr(np, 'trapezoid'):
    trapz_func = np.trapezoid
else:
    trapz_func = np.trapz

class WelchPSDAnalyzer:
    """
    Analyzes EEG signals using Welch's method to extract frequency band powers.
    Bands: Delta (0.5-4 Hz), Theta (4-8 Hz), Alpha (8-13 Hz), Beta (13-30 Hz), Gamma (30-45 Hz)
    """
    
    def __init__(self, sfreq: float = 250.0):
        self.sfreq = sfreq
        self.bands = {
            "delta": (0.5, 4.0),
            "theta": (4.0, 8.0),
            "alpha": (8.0, 13.0),
            "beta": (13.0, 30.0),
            "gamma": (30.0, 45.0)
        }
        
    def fit_transform(self, raw_data) -> dict:
        """
        Calculate PSD and band powers.
        Assumes input is MNE Raw object or numpy array (channels x time).
        """
        # Extract data array
        if hasattr(raw_data, 'get_data'):
            data = raw_data.get_data()
            sfreq = raw_data.info['sfreq']
        else:
            data = np.asarray(raw_data)
            sfreq = self.sfreq
            
        # If 2D (multi-channel), average across channels for a global estimate
        if data.ndim == 2:
            data = np.mean(data, axis=0)
            
        # Ensure 1D array
        data = data.flatten()
        
        # Calculate Welch PSD
        # nperseg = 2 seconds of data for good frequency resolution
        nperseg = int(2.0 * sfreq)
        freqs, psd = signal.welch(data, fs=sfreq, nperseg=min(nperseg, len(data)//2))
        
        # Calculate band powers
        band_powers = {}
        total_power = 0.0
        
        for band_name, (low, high) in self.bands.items():
            # Find indices for this band
            idx_band = np.logical_and(freqs >= low, freqs <= high)
            # Integrate PSD over the band (trapezoidal rule)
            power = trapz_func(psd[idx_band], freqs[idx_band])
            band_powers[f"{band_name}_abs"] = round(float(power), 4)
            total_power += power
            
        # Calculate relative powers (percentage)
        for band_name in self.bands.keys():
            abs_power = band_powers[f"{band_name}_abs"]
            rel_power = (abs_power / total_power * 100.0) if total_power > 0 else 0.0
            band_powers[f"{band_name}_rel_pct"] = round(float(rel_power), 2)
            
        # Find peak frequency
        peak_idx = np.argmax(psd)
        peak_freq = float(freqs[peak_idx])
        
        return {
            "status": "valid",
            "peak_frequency_hz": round(peak_freq, 2),
            "band_powers": band_powers,
            "total_power": round(float(total_power), 4),
            "dominant_band": max(self.bands.keys(), key=lambda b: band_powers[f"{b}_rel_pct"])
        }
