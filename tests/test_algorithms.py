"""
Tests for PhysioSignal OS algorithms.
"""
import pytest
import numpy as np
import mne
from pathlib import Path

def test_ecg_subspace_remover_initialization():
    """Test ECG Subspace Remover can be initialized."""
    from physiosignal.algorithms.emg.ecg_subspace_remover import ECGSubspaceRemover
    
    remover = ECGSubspaceRemover(
        ref_channel_idx='auto',
        ecg_max_freq=25.0,
        subtraction_strength=1.5
    )
    
    assert remover.ecg_max_freq == 25.0
    assert remover.subtraction_strength == 1.5
    assert remover.ref_channel_idx == 'auto'

def test_hrv_analyzer_initialization():
    """Test HRV Analyzer can be initialized."""
    from physiosignal.algorithms.ecg.hrv_analyzer import HRVAnalyzer
    
    analyzer = HRVAnalyzer(sfreq=250.0)
    assert analyzer.sfreq == 250.0

def test_hrv_analyzer_with_synthetic_ecg():
    """Test HRV Analyzer with synthetic ECG-like signal."""
    from physiosignal.algorithms.ecg.hrv_analyzer import HRVAnalyzer
    
    # Create synthetic ECG-like signal with peaks every 0.8s (75 BPM)
    sfreq = 250.0
    duration = 10.0
    t = np.linspace(0, duration, int(sfreq * duration))
    
    # Simulate R-peaks at 75 BPM (every 0.8s)
    peak_times = np.arange(0, duration, 0.8)
    peak_indices = (peak_times * sfreq).astype(int)
    
    signal = np.zeros_like(t)
    for idx in peak_indices:
        if idx < len(signal):
            signal[idx] = 1.0
    
    # Add some noise
    signal += np.random.randn(len(signal)) * 0.1
    
    analyzer = HRVAnalyzer(sfreq=sfreq)
    metrics = analyzer.fit_transform(signal)
    
    assert 'n_peaks_detected' in metrics
    assert 'mean_hr_bpm' in metrics
    assert metrics['n_peaks_detected'] > 5

def test_subspace_remover_with_test_data():
    """Test Subspace Remover with actual test data if available."""
    from physiosignal.algorithms.emg.ecg_subspace_remover import ECGSubspaceRemover
    
    mixture_files = list(Path("results/mixtures/SUBJ_01").glob("mixture_snr-5_seed*-raw.fif"))
    
    if not mixture_files:
        pytest.skip("No test data available")
    
    raw = mne.io.read_raw_fif(mixture_files[0], verbose=False)
    
    remover = ECGSubspaceRemover(
        ref_channel_idx='auto',
        ecg_max_freq=25.0,
        subtraction_strength=1.5
    )
    
    raw_clean = remover.fit_transform(raw)
    
    assert raw_clean is not None
    assert raw_clean.get_data().shape == raw.get_data().shape
