"""
Test script with TWO independent controls.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import mne
import numpy as np

from ecg_in_emg.algorithms.event_aligned_subspace import ECGSubspaceRemover


def main():
    mixture_path = Path("results/mixtures/SUBJ_01/mixture_snr-5_seed924682273-raw.fif")
    clean_path = Path("results/mixtures/SUBJ_01/clean_snr-5_seed924682273-raw.fif")

    if not mixture_path.exists():
        print("❌ Mixture file not found.")
        return

    raw_mixture = mne.io.read_raw_fif(mixture_path, verbose=False)
    raw_clean_ref = mne.io.read_raw_fif(clean_path, verbose=False)

    print(
        f"Loaded data: {raw_mixture.info['nchan']} channels, {raw_mixture.info['sfreq']} Hz"
    )

    # ==========================================
    # 🎛️ KNOB 1: Frequency Isolation
    # Lower = more conservative (protects EMG)
    # Higher = more aggressive (removes more ECG)
    # Try: 15, 20, 25, 30, 35, 40
    ECG_MAX_FREQ = 25

    # 🎛️ KNOB 2: Subtraction Strength
    # 0.5 = gentle, 1.0 = standard, 1.5 = aggressive
    # Try: 0.5, 0.75, 1.0, 1.25, 1.5, 2.0
    SUBTRACTION_STRENGTH = 1.8
    # ==========================================

    remover = ECGSubspaceRemover(
        ref_channel_idx=0,
        window=(-0.15, 0.35),
        n_components=2,
        bandpass_freqs=(5.0, 15.0),
        peak_threshold=0.5,
        ecg_max_freq=ECG_MAX_FREQ,
        subtraction_strength=SUBTRACTION_STRENGTH,
    )

    raw_restored = remover.fit_transform(raw_mixture)

    # Visualize
    sfreq = raw_mixture.info["sfreq"]
    t_max_plot = 3.0
    n_samples = int(t_max_plot * sfreq)
    t = np.arange(n_samples) / sfreq

    data_mixture = raw_mixture.get_data()[0, :n_samples]
    data_restored = raw_restored.get_data()[0, :n_samples]
    data_clean_ref = raw_clean_ref.get_data()[0, :n_samples]

    plt.figure(figsize=(12, 8))

    plt.subplot(3, 1, 1)
    plt.plot(t, data_mixture * 1e6, color="red", alpha=0.7, label="Contaminated")
    plt.title("Stage 1: ECG-Contaminated EMG", fontweight="bold")
    plt.ylabel("Amplitude (µV)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(3, 1, 2)
    plt.plot(
        t,
        data_restored * 1e6,
        color="blue",
        linewidth=1.5,
        label=f"Restored (freq={ECG_MAX_FREQ}Hz, strength={SUBTRACTION_STRENGTH})",
    )
    plt.title("Stage 2: Restored EMG", fontweight="bold")
    plt.ylabel("Amplitude (µV)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(3, 1, 3)
    plt.plot(
        t,
        data_clean_ref * 1e6,
        color="green",
        alpha=0.6,
        linestyle="--",
        label="Ground Truth",
    )
    plt.plot(t, data_restored * 1e6, color="blue", alpha=0.8, label="Restored")
    plt.title("Stage 3: Comparison vs Ground Truth", fontweight="bold")
    plt.xlabel("Time (s)")
    plt.ylabel("Amplitude (µV)")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("results/restoration_test.png", dpi=300, bbox_inches="tight")
    print(f"✅ Settings: freq={ECG_MAX_FREQ}Hz, strength={SUBTRACTION_STRENGTH}")
    print(f"✅ Visualization saved to results/restoration_test.png")
    plt.show()


if __name__ == "__main__":
    main()
