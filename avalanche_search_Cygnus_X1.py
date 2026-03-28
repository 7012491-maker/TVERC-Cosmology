# Install the necessary libraries for gravitational wave data analysis
!pip install -q gwpy
!pip install -q lalsuite

import numpy as np
import matplotlib.pyplot as plt
from gwpy.timeseries import TimeSeries
from scipy.signal import savgol_filter
import scipy.constants as const
import warnings
import gc

# Suppress warnings for cleaner academic output
warnings.filterwarnings('ignore')

# --- PARAMETERS FOR CYGNUS X-1 ---
mass_sun_equivalent = 21.2
C = const.c 
G = const.G 
M_SUN = 1.98847e30 

# --- HIGH-RES AVALANCHE SEARCH SETTINGS ---
flare_gps = 1242460000 
start_on = flare_gps + (45 * 60)
end_on = flare_gps + (60 * 60)

# --- REFERENCE BACKGROUND (CALIBRATION FROM A QUIET PERIOD) ---
start_off = flare_gps - (240 * 60)
end_off = start_off + (15 * 60)

# Target frequency window for TVERC detection
f0_min, f0_max = 720, 800

# =======================================================
# SMOOTHING INTENSITY (Integer)
# 1 = Raw data (sharpest resolution)
# 3, 5, 7, 10+ = Progressive levels of smoothing
# =======================================================
smoothing_level = 1

def get_high_res_spectrum(start, end, label):
    """Fetches LIGO data and returns the coherence spectrum within the target band."""
    print(f"[{label}] Fetching data: {start} - {end} GPS...")
    try:
        h1 = TimeSeries.fetch_open_data('H1', start, end, cache=True)
        l1 = TimeSeries.fetch_open_data('L1', start, end, cache=True)
        
        if h1 is None or l1 is None: return None, None

        # Standard whitening to normalize the background noise floor
        h1_w = h1.whiten()
        l1_w = l1.whiten()
        
        # High-resolution coherence calculation
        coh = h1_w.coherence(l1_w, fftlength=8, overlap=4)
        
        f_vals = coh.frequencies.value
        c_vals = np.nan_to_num(coh.value)

        mask = (f_vals >= f0_min) & (f_vals <= f0_max)
        return f_vals[mask], c_vals[mask]

    except Exception as e:
        print(f"  -> Processing Error: {e}")
        return None, None

def run_avalanche_search():
    """Executes the TVERC single-point calibration search and identifies the maximum peak."""
    print("\n--- LAUNCHING TVERC SINGLE CALIBRATION (V8.3) ---")
    
    freqs, bg_spectrum = get_high_res_spectrum(start_off, end_off, "BKG (OFF)")
    _, flare_spectrum = get_high_res_spectrum(start_on, end_on, "SIG (ON)")

    if bg_spectrum is not None and flare_spectrum is not None:
        print("Data processed. Identifying resonance peaks...")
        
        # Calculate Net Excess Coherence
        diff_signal = flare_spectrum - bg_spectrum
        
        # Robust smoothing logic
        if smoothing_level <= 1:
            smoothed_diff = diff_signal
            plot_label = 'Raw Acoustic Hum (No Smoothing)'
        else:
            win_len = smoothing_level if smoothing_level % 2 != 0 else smoothing_level + 1
            poly = 3 if win_len >= 5 else 1
            smoothed_diff = savgol_filter(diff_signal, win_len, poly)
            plot_label = f'Filtered Acoustic Hum (Smooth: {win_len})'

        # Large-scale figure for 2x font readability
        plt.figure(figsize=(20, 12))
        ax = plt.gca()
        plt.axhline(0, color='gray', linestyle='--', lw=1.5, alpha=0.7)
        
        # Plot the resonance curve (Color changed to dodgerblue)
        plt.plot(freqs, smoothed_diff, color='darkred', lw=3, label=plot_label)

        # --- PEAK DETECTION (MAXIMUM ONLY) ---
        max_idx = np.argmax(smoothed_diff)
        peak_freq = freqs[max_idx]
        peak_amp = smoothed_diff[max_idx]
        
        # Annotate the Maximum Peak (Color matched to the line)
        plt.annotate(f'MAX: {peak_freq:.1f} Hz\nCoh: {peak_amp:.4f}', xy=(peak_freq, peak_amp), xytext=(0, 20), 
                     textcoords='offset points', ha='center', va='bottom',
                     fontsize=20, fontweight='bold', color='dodgerblue',
                     bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.95, edgecolor='dodgerblue'))

        # --- LARGE INFORMATION BOX (BOTTOM LEFT) ---
        on_offset_min = int((start_on - flare_gps)/60)
        on_offset_max = int((end_on - flare_gps)/60)
        off_offset_min = int((start_off - flare_gps)/60)
        
        info_text = (
            f"flare_gps   = {flare_gps}\n"
            f"start_on    = flare_gps + {on_offset_min}m\n"
            f"end_on      = flare_gps + {on_offset_max}m\n"
            f"start_off   = flare_gps {'+' if off_offset_min >= 0 else ''}{off_offset_min}m\n"
            f"f0_min/max  = {f0_min}, {f0_max} Hz\n"
            f"smoothing   = {smoothing_level}"
        )
        
        props = dict(boxstyle='round', facecolor='whitesmoke', alpha=0.95, edgecolor='gray')
        ax.text(0.02, 0.02, info_text, transform=ax.transAxes, fontsize=18,
                family='monospace', verticalalignment='bottom', bbox=props)

        # Axis scaling and formatting
        plt.xlim(f0_min, f0_max)
        y_max, y_min = np.nanmax(smoothed_diff), np.nanmin(smoothed_diff)
        plt.ylim(y_min - abs(y_min * 0.4), y_max + abs(y_max * 0.4))
        
        # 2x font sizes for Academic Output
        plt.title(f'TVERC AVALANCHE SEARCH: Single Calibration\n'
                  f'Object: Cygnus X-1, Window: +{on_offset_min} to +{on_offset_max} min', 
                  fontsize=28, fontweight='bold', pad=25)
        plt.xlabel('Frequency (Hz)', fontsize=24)
        plt.ylabel('Net Excess Coherence', fontsize=24)
        plt.xticks(fontsize=20)
        plt.yticks(fontsize=20)
        
        plt.grid(True, which='both', linestyle=':', alpha=0.5)
        plt.legend(loc='upper right', fontsize=20)
        plt.tight_layout()
        
        # Memory management
        del freqs, bg_spectrum, flare_spectrum, diff_signal, smoothed_diff
        gc.collect()
        
        plt.show()
    else:
        print("\nCRITICAL ERROR: Analysis aborted due to missing LIGO data segments.")

run_avalanche_search()
