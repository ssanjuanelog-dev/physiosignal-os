# ECG-in-EMG: Task-Preserving Artifact Removal Benchmark

**Author:** Santiago Gomez  
**Domain:** Biomedical Signal Processing / Machine Learning Data Prep  
**Focus:** EMG/ECG Time-Series Analysis, Blind Source Separation, and Feature Extraction  

## 🎯 Objective
This repository provides a production-grade, leakage-proof benchmark and toolkit for removing structured physiological interference (specifically ECG contamination) from multi-channel surface EMG. 

Unlike naive filtering or basic ICA, this tool treats the ECG artifact as a **quasi-periodic, event-locked source**, applying a "Demucs-style" subspace cancellation that preserves the high-frequency motor-unit action potentials critical for downstream gesture and force decoding.

## ⚠️ The Problem with Standard Pipelines
1. **High-pass filtering destroys information:** Removing frequencies <20Hz to eliminate ECG also destroys the low-frequency EMG envelope, degrading force-estimation models.
2. **Naive template subtraction causes "anti-peaks":** Global subtraction assumes all ECG beats have identical amplitude, leading to over-subtraction (holes in the signal) or under-subtraction (residual spikes).
3. **Lack of reproducible benchmarks:** Most denoising papers use synthetic noise that doesn't reflect real-world spatial mixing.

## 🛠️ The Solution: Per-Beat Adaptive Subspace Cancellation
Drawing from professional audio restoration techniques, this pipeline implements a 4-step "wave specialist" approach:

1. **Event Detection:** Isolates QRS complexes using a bandpass-filtered reference channel.
2. **Spectral Isolation:** Low-pass filters (<25Hz) the extracted epochs to build a pure ECG spatial template, completely stripping out high-frequency EMG contamination.
3. **Per-Beat Adaptive Scaling:** Calculates the exact amplitude ratio of *each individual beat* against the template, applying a dynamic gain to prevent over/under-subtraction artifacts.
4. **Smooth Gated Subtraction:** Applies a Hann window mask to the subtraction, ensuring zero boundary discontinuities ("clicks") in the restored signal.

## 🏗️ Architecture
- `src/ecg_in_emg/mixture/generator.py`: Deterministic, leakage-proof mixture generation with SHA-256 seeded provenance.
- `src/ecg_in_emg/algorithms/event_aligned_subspace.py`: The core `ECGSubspaceRemover` (scikit-learn compatible `TransformerMixin`).
- `scripts/`: Reproducible pipelines for building mixtures and generating portfolio visualizations.

## 🚀 How to Run
1. Install dependencies: `pip install -e ".[dev]"`
2. Generate reproducible benchmark mixtures: `python scripts/build_mixtures.py --test-mode`
3. Run the final portfolio visualization: `python scripts/final_portfolio_viz.py`

## 🤖 Connection to AI & Foundational Models
Advanced ML models (e.g., for BCI or prosthetic control) are fundamentally limited by the quality of their training data. By delivering a high-SNR, morphologically pure EMG signal, this pipeline ensures that downstream classifiers learn true motor intent rather than memorizing ECG artifact correlations.

## 📜 License
MIT License.
