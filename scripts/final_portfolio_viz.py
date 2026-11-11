"""
Final Portfolio Visualization: Demonstrates robustness across multiple SNR levels.
"""
import mne
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from ecg_in_emg.algorithms.event_aligned_subspace import ECGSubspaceRemover

def main():
    snr_levels = [-10, -5, 0]
    subject = "SUBJ_01"
    donor = "ECG_DONOR_A"
    
    fig, axes = plt.subplots(len(snr_levels), 1, figsize=(14, 10), sharex=True)
    
    for idx, snr in enumerate(snr_levels):
        # Find the seed for this SNR from the manifest
        import pandas as pd
        manifest = pd.read_csv("results/mixtures/mixture_manifest.csv")
        row = manifest[(manifest['emg_subject'] == subject) & 
                       (manifest['ecg_donor'] == donor) & 
                       (manifest['target_snr_db'] == snr)].iloc[0]
        seed = row['seed']
        
        mixture_path = Path(f"results/mixtures/{subject}/mixture_snr{snr}_seed{seed}-raw.fif")
        clean_path = Path(f"results/mixtures/{subject}/clean_snr{snr}_seed{seed}-raw.fif")
        
        raw_mixture = mne.io.read_raw_fif(mixture_path, verbose=False)
        raw_clean_ref = mne.io.read_raw_fif(clean_path, verbose=False)
        
        # Apply the algorithm with tuned defaults
        remover = ECGSubspaceRemover()
        raw_restored = remover.fit_transform(raw_mixture)
        
        # Plot first 2 seconds of Channel 1
        sfreq = raw_mixture.info['sfreq']
        n_samples = int(2.0 * sfreq)
        t = np.arange(n_samples) / sfreq
        
        data_mixture = raw_mixture.get_data()[0, :n_samples]
        data_restored = raw_restored.get_data()[0, :n_samples]
        data_clean_ref = raw_clean_ref.get_data()[0, :n_samples]
        
        ax = axes[idx]
        ax.plot(t, data_mixture * 1e6, color='red', alpha=0.5, label='Contaminated', linewidth=1)
        ax.plot(t, data_restored * 1e6, color='blue', linewidth=1.5, label='Restored (Ours)')
        ax.plot(t, data_clean_ref * 1e6, color='green', alpha=0.7, linestyle='--', label='Ground Truth', linewidth=1)
        
        ax.set_title(f'SNR = {snr} dB', fontweight='bold', loc='left')
        ax.set_ylabel('Amplitude (µV)')
        ax.legend(loc='upper right', fontsize=8)
        ax.grid(True, alpha=0.3)
        
    axes[-1].set_xlabel('Time (s)')
    plt.suptitle('ECG Artifact Removal: Robustness Across SNR Levels (Channel EMG01)', fontweight='bold', fontsize=14, y=0.98)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    plt.savefig('results/portfolio_final_comparison.png', dpi=300, bbox_inches='tight')
    print("✅ Final portfolio visualization saved to: results/portfolio_final_comparison.png")
    plt.show()

if __name__ == "__main__":
    main()
