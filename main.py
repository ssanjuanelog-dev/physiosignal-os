#!/usr/bin/env python3
"""
PhysioSignal OS - Main Entry Point
Plug-and-play execution for physiological signal processing.
"""
import sys
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)-8s | %(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("🚀 Starting PhysioSignal OS Pipeline...")
    
    Path("results/mixtures").mkdir(parents=True, exist_ok=True)
    Path("results/audit").mkdir(parents=True, exist_ok=True)
    
    logger.info("Step 1/4: Checking physiological data...")
    try:
        from physiosignal.mixture.generator import build_mixture_manifest, process_manifest_row
        import pandas as pd
        
        manifest_path = Path("results/mixtures/mixture_manifest.csv")
        if not manifest_path.exists():
            logger.info("Generating realistic MUAP + PhysioNet ECG mixtures...")
            manifest = build_mixture_manifest(Path("results/mixtures"), test_mode=True)
            for _, row in manifest.iterrows():
                process_manifest_row(row, Path("results/mixtures"), test_mode=True)
            logger.info("✅ Data generation complete.")
        else:
            logger.info("✅ Data already exists. Skipping generation.")
    except Exception as e:
        logger.error(f"Failed to generate data: {e}")
        sys.exit(1)

    logger.info("Step 2/4: Running SOTA ECG Subspace Canceller...")
    try:
        import mne
        from physiosignal.algorithms.emg.ecg_subspace_remover import ECGSubspaceRemover
        from physiosignal.integrity import get_audit_log
        
        mixture_file = list(Path("results/mixtures/SUBJ_01").glob("mixture_snr-5_seed*-raw.fif"))[0]
        raw_mixture = mne.io.read_raw_fif(mixture_file, verbose=False)
        
        audit = get_audit_log(patient_id="DEMO_PATIENT_001")
        audit.add_entry("LOAD", {"file": str(mixture_file.name)})
        
        remover = ECGSubspaceRemover(
            ref_channel_idx='auto',
            ecg_max_freq=25.0,
            subtraction_strength=1.5
        )
        raw_clean = remover.fit_transform(raw_mixture)
        
        audit.add_entry("PROCESS", {
            "algorithm": "ECG Subspace Canceller",
            "ref_channels": remover.detected_ref_channel_,
            "strength": 1.5
        })
        
        clean_file = mixture_file.parent / f"clean_{mixture_file.name}"
        raw_clean.save(clean_file, overwrite=True, verbose=False)
        logger.info(f"✅ Processing complete. Saved to {clean_file.name}")
        
    except Exception as e:
        logger.error(f"Algorithm execution failed: {e}")
        sys.exit(1)

    logger.info("Step 3/4: Generating cryptographic audit trail...")
    log_path = audit.save()
    logger.info(f"✅ Audit log saved: {log_path.name}")
    
    logger.info("Step 4/4: Launching Dashboard...")
    try:
        import webbrowser
        dashboard_path = Path("results/dashboard.html")
        if dashboard_path.exists():
            webbrowser.open('file://' + str(dashboard_path.absolute()))
            logger.info("✅ Dashboard opened in your default browser.")
        else:
            logger.warning("⚠️ Dashboard HTML not found.")
    except Exception as e:
        logger.error(f"Failed to open dashboard: {e}")

    logger.info("🎉 PhysioSignal OS pipeline completed successfully!")

if __name__ == "__main__":
    main()
