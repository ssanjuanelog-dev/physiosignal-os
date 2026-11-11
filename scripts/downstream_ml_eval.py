"""
Downstream ML Evaluation: Proves that artifact removal preserves critical EMG features.
"""
import numpy as np
import mne
import matplotlib.pyplot as plt
import logging
from pathlib import Path
from scipy.signal import welch
from ecg_in_emg.algorithms.event_aligned_subspace import ECGSubspaceRemover

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

def extract_epoch_features(data, sfreq):
    n_channels, n_times = data.shape
    epoch_len = int(sfreq * 1.0)
    n_epochs = n_times // epoch_len
    
    features = []
    for i in range(n_epochs):
        epoch_data = data[:, i*epoch_len : (i+1)*epoch_len]
        rms = np.sqrt(np.mean(epoch_data**2, axis=1))
        mav = np.mean(np.abs(epoch_data), axis=1)
        
        mdf = np.zeros(n_channels)
        for ch in range(n_channels):
            freqs, psd = welch(epoch_data[ch], fs=sfreq, nperseg=min(256, epoch_len))
            cum_psd = np.cumsum(psd)
            mdf[ch] = freqs[np.searchsorted(cum_psd, cum_psd[-1]/2)]
            
        features.append(np.concatenate([rms, mav, mdf]))
    return np.array(features)

def main():
    subject = "SUBJ_01"
    snr = -5
    # CORRECTED SEED from the new physiological manifest
    seed = 2126519587 
    
    mixture_path = Path(f"results/mixtures/{subject}/mixture_snr{snr}_seed{seed}-raw.fif")
    clean_path = Path(f"results/mixtures/{subject}/clean_snr{snr}_seed{seed}-raw.fif")
    
    if not mixture_path.exists():
        logger.error(f"Mixture not found at {mixture_path}. Run build_mixtures.py first.")
        return
        
    raw_mixture = mne.io.read_raw_fif(mixture_path, verbose=False)
    raw_clean = mne.io.read_raw_fif(clean_path, verbose=False)
    sfreq = raw_mixture.info['sfreq']
    
    logger.info("Applying ECG Subspace Remover...")
    remover = ECGSubspaceRemover(ecg_max_freq=25.0, subtraction_strength=1.5)
    raw_restored = remover.fit_transform(raw_mixture)
    
    logger.info("Extracting ML features (RMS, MAV, MDF) per 1-second epoch...")
    feat_clean = extract_epoch_features(raw_clean.get_data(), sfreq)
    feat_mixture = extract_epoch_features(raw_mixture.get_data(), sfreq)
    feat_restored = extract_epoch_features(raw_restored.get_data(), sfreq)
    
    error_mixture = np.mean(np.abs(feat_mixture - feat_clean), axis=0)
    error_restored = np.mean(np.abs(feat_restored - feat_clean), axis=0)
    
    mean_error_mixture = np.mean(error_mixture)
    mean_error_restored = np.mean(error_restored)
    improvement_pct = ((mean_error_mixture - mean_error_restored) / mean_error_mixture) * 100
    
    logger.info(f"Mean Feature Error (Mixture):  {mean_error_mixture:.4e}")
    logger.info(f"Mean Feature Error (Restored): {mean_error_restored:.4e}")
    logger.info(f"✅ Feature Preservation Improvement: {improvement_pct:.1f}%")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    ax1.bar(['RMS', 'MAV', 'MDF'], 
            [error_mixture[0], error_mixture[1], error_mixture[2]], 
            color='red', alpha=0.6, label='Contaminated Error', width=0.4)
    ax1.bar(['RMS', 'MAV', 'MDF'], 
            [error_restored[0], error_restored[1], error_restored[2]], 
            color='blue', alpha=0.8, label='Restored Error', width=0.4)
    
    ax1.set_title('Feature Extraction Error vs Ground Truth\n(Lower is Better)', fontweight='bold')
    ax1.set_ylabel('Mean Absolute Error')
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    
    t = np.arange(feat_clean.shape[0])
    ax2.plot(t, feat_clean[:, 0], color='green', linestyle='--', linewidth=2, label='Ground Truth RMS')
    ax2.plot(t, feat_mixture[:, 0], color='red', alpha=0.5, label='Contaminated RMS')
    ax2.plot(t, feat_restored[:, 0], color='blue', linewidth=1.5, label='Restored RMS')
    
    ax2.set_title('RMS Feature Over Time (Channel 1)\nCritical for Force Estimation', fontweight='bold')
    ax2.set_xlabel('Time (seconds)')
    ax2.set_ylabel('RMS Amplitude')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle(f'Downstream ML Feature Preservation (SNR {snr}dB) | Improvement: {improvement_pct:.1f}%', 
                 fontweight='bold', fontsize=14, y=1.05)
    plt.tight_layout()
    plt.savefig('results/ml_feature_preservation.png', dpi=300, bbox_inches='tight')
    logger.info("✅ Visualization saved to results/ml_feature_preservation.png")
    plt.show()

if __name__ == "__main__":
    main()
