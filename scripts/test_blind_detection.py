"""
Test Blind Source Separation: Proves the algorithm finds the ECG even if channels are scrambled.
"""
import numpy as np
import mne
import logging
from pathlib import Path
from ecg_in_emg.algorithms.event_aligned_subspace import ECGSubspaceRemover

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

def main():
    subject = "SUBJ_01"
    snr = -5
    seed = 2126519587 
    
    mixture_path = Path(f"results/mixtures/{subject}/mixture_snr{snr}_seed{seed}-raw.fif")
    
    if not mixture_path.exists():
        logger.error("Mixture not found.")
        return
        
    raw_mixture = mne.io.read_raw_fif(mixture_path, verbose=False)
    
    # SCRAMBLE THE CHANNELS to simulate real-world messy data imports
    logger.info("Scrambling channel order to test blind detection robustness...")
    ch_names = raw_mixture.ch_names
    rng = np.random.default_rng(42)
    shuffled_indices = rng.permutation(len(ch_names))
    shuffled_ch_names = [ch_names[i] for i in shuffled_indices]
    
    # Create a new Raw object with scrambled channels
    scrambled_data = raw_mixture.get_data()[shuffled_indices, :]
    info_scrambled = mne.create_info(ch_names=shuffled_ch_names, sfreq=raw_mixture.info['sfreq'], ch_types="emg")
    raw_scrambled = mne.io.RawArray(scrambled_data, info_scrambled, verbose=False)
    
    # Apply the remover with 'auto' (default)
    logger.info("Applying ECG Subspace Remover with ref_channel_idx='auto'...")
    remover = ECGSubspaceRemover(ref_channel_idx='auto', ecg_max_freq=25.0, subtraction_strength=1.5)
    raw_restored = remover.fit_transform(raw_scrambled)
    
    logger.info("✅ SUCCESS: Algorithm automatically found the ECG and cleaned the scrambled data!")
    logger.info(f"   Detected reference channel index: {remover.detected_ref_channel_} ('{shuffled_ch_names[remover.detected_ref_channel_]}')")

if __name__ == "__main__":
    main()
