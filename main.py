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
    Path("results/reports").mkdir(parents=True, exist_ok=True)
    
    logger.info("Step 1/4: Checking physiological data...")
    try:
        from physiosignal.mixture.generator import build_mixture_manifest, process_manifest_row
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

    logger.info("Step 2/4: Running SOTA Algorithms...")
    try:
        import mne
        import numpy as np
        from physiosignal.algorithms.emg.ecg_subspace_remover import ECGSubspaceRemover
        from physiosignal.algorithms.ecg.hrv_analyzer import HRVAnalyzer
        from physiosignal.integrity import get_audit_log, hash_array
        from physiosignal.integrity.report_generator import ClinicalReportGenerator
        
        mixture_file = list(Path("results/mixtures/SUBJ_01").glob("mixture_snr-5_seed*-raw.fif"))[0]
        raw_mixture = mne.io.read_raw_fif(mixture_file, verbose=False)
        
        audit = get_audit_log(patient_id="DEMO_PATIENT_001")
        audit.add_entry("LOAD", {"file": str(mixture_file.name)})
        
        # 1. Clean the signal
        remover = ECGSubspaceRemover(ref_channel_idx='auto', ecg_max_freq=25.0, subtraction_strength=1.5)
        raw_clean = remover.fit_transform(raw_mixture)
        
        input_hash = hash_array(raw_mixture.get_data())
        output_hash = hash_array(raw_clean.get_data())
        
        audit.add_entry("PROCESS", {"algorithm": "ECG Subspace Canceller", "strength": 1.5})
        
        clean_file = mixture_file.parent / f"clean_{mixture_file.name}"
        raw_clean.save(clean_file, overwrite=True, verbose=False)
        
        # 2. Run HRV Analysis on cleaned signal
        logger.info("Running HRV Analysis on cleaned signal...")
        hrv = HRVAnalyzer(sfreq=raw_clean.info['sfreq'])
        hrv_metrics = hrv.fit_transform(raw_clean)
        audit.add_entry("ANALYSIS", {"module": "HRVAnalyzer", "metrics": hrv_metrics})
        
        logger.info(f"✅ HRV Metrics: RMSSD={hrv_metrics.get('rmssd_ms')}ms, SDNN={hrv_metrics.get('sdnn_ms')}ms")
        
    except Exception as e:
        logger.error(f"Algorithm execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    logger.info("Step 3/4: Generating Cryptographic Report...")
    try:
        report_gen = ClinicalReportGenerator(patient_id="DEMO_PATIENT_001")
        report_path = report_gen.generate(
            metrics=hrv_metrics,
            input_hash=input_hash[:16],
            output_hash=output_hash[:16],
            pipeline_name="EMG_ECG_Cleanup_HRV"
        )
        logger.info(f"✅ Signed report saved: {report_path.name}")
        audit.add_entry("REPORT_GENERATED", {"path": str(report_path.name)})
    except Exception as e:
        logger.error(f"Report generation failed: {e}")

    logger.info("Step 4/4: Saving Audit Trail and Launching Dashboard...")
    log_path = audit.save()
    logger.info(f"✅ Audit log saved: {log_path.name}")
    
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
