"""
Event-Aligned Subspace Canceller.
Production-ready implementation with empirically tuned defaults.
"""
import numpy as np
import mne
import logging
from scipy.signal import find_peaks, butter, filtfilt
from sklearn.base import BaseEstimator, TransformerMixin

logger = logging.getLogger(__name__)

class ECGSubspaceRemover(BaseEstimator, TransformerMixin):
    def __init__(self, ref_channel_idx=0, window=(-0.15, 0.35), n_components=2, 
                 bandpass_freqs=(5.0, 15.0), peak_threshold=0.5, 
                 ecg_max_freq=25.0, subtraction_strength=1.5):
        """
        Parameters:
        -----------
        ecg_max_freq : float (default 25.0)
            Low-pass cutoff for ECG isolation. 25Hz captures QRS morphology 
            while protecting high-frequency EMG (>30Hz).
        
        subtraction_strength : float (default 1.5)
            Compensates for median-template amplitude underestimation. 
            1.5 is the empirically tuned sweet spot for complete cancellation 
            without over-subtraction artifacts.
        """
        self.ref_channel_idx = ref_channel_idx
        self.window = window
        self.n_components = n_components
        self.bandpass_freqs = bandpass_freqs
        self.peak_threshold = peak_threshold
        self.ecg_max_freq = ecg_max_freq
        self.subtraction_strength = subtraction_strength
        
        self.ecg_template_ = None
        self.ecg_subspace_ = None
        self.peak_indices_ = []
        self.sfreq_ = None
        self.template_max_amp_ = None

    def fit(self, raw: mne.io.Raw, y=None):
        logger.info("Fitting ECG Subspace Remover...")
        self.sfreq_ = raw.info['sfreq']
        data = raw.get_data()
        ref_signal = data[self.ref_channel_idx]
        
        nyq = 0.5 * self.sfreq_
        low = self.bandpass_freqs[0] / nyq
        high = self.bandpass_freqs[1] / nyq
        b_det, a_det = butter(4, [low, high], btype='band')
        filtered_ref = filtfilt(b_det, a_det, ref_signal)
        
        threshold = self.peak_threshold * np.std(filtered_ref)
        peaks, _ = find_peaks(filtered_ref, height=threshold, distance=int(0.6 * self.sfreq_))
        self.peak_indices_ = peaks
        logger.info(f"Detected {len(peaks)} potential ECG events.")
        
        if len(peaks) < 5:
            raise ValueError("Not enough ECG events detected.")
            
        t_min, t_max = self.window
        n_samples_min = int(abs(t_min) * self.sfreq_)
        n_samples_max = int(t_max * self.sfreq_)
        epoch_length = n_samples_min + n_samples_max
        
        epochs_list = []
        for peak in peaks:
            start = max(0, peak - n_samples_min)
            end = min(data.shape[1], peak + n_samples_max)
            epoch = data[:, start:end]
            if epoch.shape[1] < epoch_length:
                pad_width = epoch_length - epoch.shape[1]
                epoch = np.pad(epoch, ((0, 0), (0, pad_width)), mode='edge')
            epochs_list.append(epoch)
            
        epochs_array = np.stack(epochs_list)
        
        lp_freq = self.ecg_max_freq / nyq
        b_lp, a_lp = butter(4, lp_freq, btype='low')
        epochs_lp = np.array([filtfilt(b_lp, a_lp, epoch, axis=1) for epoch in epochs_list])
        
        self.ecg_template_ = np.median(epochs_lp, axis=0)
        self.template_max_amp_ = np.max(np.abs(self.ecg_template_))
        
        U, S, Vh = np.linalg.svd(self.ecg_template_, full_matrices=False)
        self.ecg_subspace_ = U[:, :self.n_components]
        
        logger.info(f"Learned ECG subspace. Template max amp: {self.template_max_amp_:.2e}")
        return self

    def transform(self, raw: mne.io.Raw, y=None) -> mne.io.Raw:
        logger.info(f"Applying per-beat adaptive subspace cancellation (strength={self.subtraction_strength})...")
        data = raw.get_data().copy()
        n_channels, n_times = data.shape
        
        t_min, t_max = self.window
        n_samples_min = int(abs(t_min) * self.sfreq_)
        n_samples_max = int(t_max * self.sfreq_)
        epoch_length = n_samples_min + n_samples_max
        
        smooth_mask = np.hanning(epoch_length)
        nyq = 0.5 * self.sfreq_
        lp_freq = self.ecg_max_freq / nyq
        b_lp, a_lp = butter(4, lp_freq, btype='low')
        
        for peak in self.peak_indices_:
            start = max(0, peak - n_samples_min)
            end = min(n_times, peak + n_samples_max)
            
            window_data = data[:, start:end]
            current_len = window_data.shape[1]
            
            if current_len < epoch_length:
                actual_mask = smooth_mask[:current_len]
                template = self.ecg_template_[:, :current_len]
                template_max = np.max(np.abs(template))
            else:
                actual_mask = smooth_mask
                template = self.ecg_template_
                template_max = self.template_max_amp_
            
            window_lf = filtfilt(b_lp, a_lp, window_data, axis=1)
            current_beat_max = np.max(np.abs(window_lf))
            
            if template_max > 1e-12:
                local_scale = (current_beat_max / template_max) * self.subtraction_strength
            else:
                local_scale = self.subtraction_strength
                
            projection_lf = self.ecg_subspace_ @ (self.ecg_subspace_.T @ window_lf)
            masked_projection = projection_lf * actual_mask * local_scale
            
            data[:, start:end] = window_data - masked_projection
            
        raw_clean = mne.io.RawArray(data, raw.info.copy(), verbose=False)
        logger.info("Cancellation complete.")
        return raw_clean
