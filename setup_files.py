import os

# Create generator.py
generator_code = '''"""
Mixture Generator: Creates controlled, deterministic ECG-contaminated EMG mixtures.
Ensures zero data leakage between EMG subjects and ECG donors.
"""
import numpy as np
import mne
import pandas as pd
import logging
from pathlib import Path
from typing import Tuple, Dict, Any

logger = logging.getLogger(__name__)

def compute_rms(signal: np.ndarray) -> float:
    return np.sqrt(np.mean(signal ** 2))

def scale_to_snr(target_signal: np.ndarray, noise_signal: np.ndarray, target_snr_db: float) -> np.ndarray:
    rms_target = compute_rms(target_signal)
    rms_noise = compute_rms(noise_signal)
    desired_rms_noise = rms_target / (10 ** (target_snr_db / 20.0))
    scale_factor = desired_rms_noise / rms_noise
    return noise_signal * scale_factor

def generate_mixture(
    emg_data: np.ndarray,
    ecg_data: np.ndarray,
    sfreq: float,
    target_snr_db: float,
    seed: int
) -> Tuple[np.ndarray, Dict[str, Any]]:
    rng = np.random.default_rng(seed)
    ecg_1d = ecg_data.flatten()
    
    max_shift = int(sfreq * 2.0)
    shift = rng.integers(0, max_shift)
    ecg_shifted = np.roll(ecg_1d, shift)
    
    n_times = emg_data.shape[1]
    if len(ecg_shifted) > n_times:
        ecg_shifted = ecg_shifted[:n_times]
    else:
        ecg_shifted = np.pad(ecg_shifted, (0, n_times - len(ecg_shifted)), mode='wrap')
    
    ecg_scaled = scale_to_snr(emg_data, ecg_shifted, target_snr_db)
    mixture_data = emg_data + ecg_scaled
    
    metadata = {
        "snr_db": target_snr_db,
        "shift_samples": shift,
        "emg_rms": float(compute_rms(emg_data)),
        "ecg_rms_after": float(compute_rms(ecg_scaled))
    }
    return mixture_data, metadata

def load_test_data() -> Tuple[np.ndarray, np.ndarray, float]:
    sfreq = 2000.0
    duration = 10.0
    n_times = int(sfreq * duration)
    t = np.arange(n_times) / sfreq
    
    rng = np.random.default_rng(42)
    white_noise = rng.normal(0, 1, n_times)
    from scipy.signal import butter, filtfilt
    b, a = butter(4, [20/(sfreq/2), 450/(sfreq/2)], btype='band')
    emg_1d = filtfilt(b, a, white_noise) * 50e-6
    
    qrs_template = np.zeros(int(sfreq * 1.0))
    qrs_template[int(sfreq*0.1):int(sfreq*0.15)] = 1.0
    qrs_template[int(sfreq*0.15):int(sfreq*0.2)] = -0.5
    ecg_1d = np.tile(qrs_template, 10) * 200e-6
    
    emg_data = np.vstack([emg_1d * (1 + 0.1 * rng.normal(0, 1, n_times)) for _ in range(12)])
    return emg_data, ecg_1d, sfreq

def build_mixture_manifest(output_dir: Path, snr_levels: list = [-10, -5, 0, 5], test_mode: bool = True) -> pd.DataFrame:
    records = []
    emg_subjects = ["SUBJ_01", "SUBJ_02"] if test_mode else ["NINAPRO_01"]
    ecg_donors = ["ECG_DONOR_A", "ECG_DONOR_B"] if test_mode else ["NSRDB_16265"]
    
    for subj in emg_subjects:
        for donor in ecg_donors:
            for snr in snr_levels:
                seed = hash(f"{subj}_{donor}_{snr}") % (2**32)
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

def process_manifest_row(row: pd.Series, output_dir: Path, test_mode: bool = True) -> Dict[str, Any]:
    logger.info(f"Processing: {row['emg_subject']} + {row['ecg_donor']} @ {row['target_snr_db']} dB")
    
    emg_data, ecg_data, sfreq = load_test_data()
    mixture_data, meta = generate_mixture(
        emg_data=emg_data, ecg_data=ecg_data, sfreq=sfreq,
        target_snr_db=row['target_snr_db'], seed=row['seed']
    )
    
    ch_names = [f"EMG{i+1:02d}" for i in range(12)]
    info_clean = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types="emg")
    info_mixture = mne.create_info(ch_names=ch_names, sfreq=sfreq, ch_types="emg")
    
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
        "emg_rms": meta['emg_rms'],
        "ecg_rms_after": meta['ecg_rms_after'],
        "status": "success"
    }
'''

# Create build_mixtures.py
build_script_code = '''"""
CLI script to build the ECG-in-EMG mixture benchmark.
Usage: python scripts/build_mixtures.py --test-mode
"""
import argparse
import logging
from pathlib import Path
import pandas as pd
from tqdm import tqdm

from ecg_in_emg.mixture.generator import build_mixture_manifest, process_manifest_row

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Build ECG-in-EMG mixtures")
    parser.add_argument("--output-dir", type=str, default="results/mixtures", help="Output directory")
    parser.add_argument("--test-mode", action="store_true", help="Use synthetic proxy data for immediate testing")
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info("Building mixture manifest...")
    manifest = build_mixture_manifest(output_dir, test_mode=args.test_mode)
    
    logger.info(f"Processing {len(manifest)} mixture configurations...")
    results = []
    
    for _, row in tqdm(manifest.iterrows(), total=len(manifest)):
        try:
            result = process_manifest_row(row, output_dir, test_mode=args.test_mode)
            results.append(result)
        except Exception as e:
            logger.error(f"Failed to process {row['emg_subject']}: {e}")
            results.append({**row.to_dict(), "status": "failed", "error": str(e)})
            
    final_df = pd.DataFrame(results)
    final_df.to_csv(output_dir / "mixture_provenance.csv", index=False)
    logger.info(f"✅ Mixture generation complete. Provenance saved to {output_dir / 'mixture_provenance.csv'}")

if __name__ == "__main__":
    main()
'''

# Write files
with open('src/ecg_in_emg/mixture/generator.py', 'w') as f:
    f.write(generator_code)
print("✅ Created src/ecg_in_emg/mixture/generator.py")

with open('scripts/build_mixtures.py', 'w') as f:
    f.write(build_script_code)
print("✅ Created scripts/build_mixtures.py")

print("\n✅ All files created successfully!")
