"""
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
