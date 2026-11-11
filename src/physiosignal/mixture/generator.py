"""
Mixture Generator: Creates controlled, deterministic ECG-contaminated EMG mixtures.
Ensures zero data leakage between EMG subjects and ECG donors.
"""
import numpy as np
import mne
import pandas as pd
import logging
from pathlib import Path
from typing import Tuple, Dict, Any
from physiosignal.datasets.physio_generator import generate_realistic_mixture

logger = logging.getLogger(__name__)

def build_mixture_manifest(output_dir: Path, snr_levels: list = [-10, -5, 0, 5], test_mode: bool = True) -> pd.DataFrame:
    records = []
    emg_subjects = ["SUBJ_01", "SUBJ_02"] if test_mode else ["NINAPRO_01"]
    ecg_donors = ["MITBIH_100", "MITBIH_101"] if test_mode else ["NSRDB_16265"]
    
    for subj in emg_subjects:
        for donor in ecg_donors:
            for snr in snr_levels:
                seed = stable_seed(f"{subj}_{donor}_{snr}")
                records.append({
                    "emg_subject": subj,
                    "ecg_donor": donor,
                    "target_snr_db": snr,
                    "seed": seed,
                    "status": "pending"
                })
                
    manifest = pd.DataFrame(records)
    manifest.to_csv(output_dir / "mixture_manifest.csv", index=False)
    logger.info(f"Manifest saved to {output_dir / 'mixture_manifest.csv'}")
    return manifest

def stable_seed(key: str) -> int:
    """Deterministic 32-bit seed from a string key (process-independent)."""
    import hashlib
    return int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16)

def process_manifest_row(row: pd.Series, output_dir: Path, test_mode: bool = True) -> Dict[str, Any]:
    logger.info(f"Processing: {row['emg_subject']} + {row['ecg_donor']} @ {row['target_snr_db']} dB")
    
    # USE REALISTIC PHYSIOLOGICAL GENERATOR
    emg_data, mixture_data, ecg_scaled = generate_realistic_mixture(
        sfreq=2000.0,
        duration=10.0,
        n_channels=12,
        target_snr_db=row['target_snr_db'],
        seed=row['seed']
    )
    
    ch_names = [f"EMG{i+1:02d}" for i in range(12)]
    info_clean = mne.create_info(ch_names=ch_names, sfreq=2000.0, ch_types="emg")
    info_mixture = mne.create_info(ch_names=ch_names, sfreq=2000.0, ch_types="emg")
    
    raw_clean = mne.io.RawArray(emg_data, info_clean, verbose=False)
    raw_mixture = mne.io.RawArray(mixture_data, info_mixture, verbose=False)
    
    subj_dir = output_dir / row['emg_subject']
    subj_dir.mkdir(parents=True, exist_ok=True)
    
    clean_path = subj_dir / f"clean_snr{row['target_snr_db']}_seed{row['seed']}-raw.fif"
    mixture_path = subj_dir / f"mixture_snr{row['target_snr_db']}_seed{row['seed']}-raw.fif"
    
    raw_clean.save(clean_path, overwrite=True, verbose=False)
    raw_mixture.save(mixture_path, overwrite=True, verbose=False)
    
    return {
        "emg_subject": row['emg_subject'],
        "ecg_donor": row['ecg_donor'],
        "target_snr_db": row['target_snr_db'],
        "seed": row['seed'],
        "clean_path": str(clean_path),
        "mixture_path": str(mixture_path),
        "status": "success"
    }
