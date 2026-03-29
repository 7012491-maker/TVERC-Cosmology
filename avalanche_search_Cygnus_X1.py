# Install the necessary libraries for gravitational wave data analysis
!pip install -q gwpy lalsuite

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
    """Fetches raw LIGO strain data and returns the true coherence spectrum.
       CRITICAL FIX: No whitening applied to preserve phase relationships."""
    print(f"[{label}] Fetching data: {start} - {end} GPS...")
    try:
        h1 = TimeSeries.fetch_open_data('H1', start, end, cache=True)
        l1 = TimeSeries.fetch_open_data('L1', start, end, cache=True)
        
        if h1 is None or l1 is None: return None, None

        # High-resolution coherence calculation directly on RAW strain data
        coh = h1.coherence(l1, fftlength=8, overlap=4)
        
        f_vals = coh.frequencies.value
        c_vals = coh.value

        mask = (f_vals >= f0_min) & (f_vals <= f0_max)
        valid_mask = mask & ~np.isnan(c_vals)
        
        return f_vals[valid_mask], c_vals[valid_mask]

    except Exception as e:
        print(f"  -> Processing Error: {e}")
        return None, None

def run_avalanche_search():
    """Executes the TVERC single-point calibration search with rigorous DSP."""
    print("\n--- LAUNCHING TVERC SINGLE CALIBRATION (V8.5 - Strict DSP + Smooth) ---")
    
    freqs_off, bg_spectrum = get_high_res_spectrum(start_off, end_off, "BKG (OFF)")
    freqs_on, flare_spectrum = get_high_res_spectrum(start_on, end_on, "SIG (ON)")

    if bg_spectrum is not None and flare_spectrum is not None:
        print("Data processed. Identifying resonance peaks...")
        
        # Large-scale figure for 2x font readability
        plt.figure(figsize=(20, 12))
        ax = plt.gca()
        
        # Plot Background (Always raw)
        plt.plot(freqs_off, bg_spectrum, color='gray', lw=1.5, alpha=0.7, label='Background Coherence (OFF)')
        
        # Determine smoothing logic for the Signal (ON)
        if smoothing_level <= 1:
            plot_signal = flare_spectrum
            plt.plot(freqs_on, plot_signal, color='darkred', lw=3, label='Raw Acoustic Hum (ON)')
        else:
            # Apply Savitzky-Golay filter to the signal
            win_len = smoothing_level if smoothing_level % 2 != 0 else smoothing_level + 1
            poly = 3 if win_len >= 5 else 1
            plot_signal = savgol_filter(flare_spectrum, win_len, poly)
            
            # Plot the raw signal faintly in the background for transparency
            plt.plot(freqs_on, flare_spectrum, color='lightcoral', lw=1.5, alpha=0.5, label='Raw Signal (Transparent)')
            # Plot the smoothed signal on top
            plt.plot(freqs_on, plot_signal, color='darkred', lw=3, label=f'Filtered Hum (Smooth: {win_len})')

        # --- PEAK DETECTION (ON PLOTTED SIGNAL) ---
        max_idx = np.argmax(plot_signal)
        peak_freq = freqs_on[max_idx]
        peak_amp = plot_signal[max_idx]
        bg_at_peak = np.interp(peak_freq, freqs_off, bg_spectrum)
        
        # Annotate the Maximum Peak (Color matched to original dodgerblue style)
        plt.annotate(f'MAX ON: {peak_freq:.2f} Hz\nCoh: {peak_amp:.4f}\n(Bkg: {bg_at_peak:.4f})', 
                     xy=(peak_freq, peak_amp), xytext=(0, 25), 
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
        y_max = max(np.max(plot_signal), np.max(bg_spectrum), np.max(flare_spectrum))
        plt.ylim(0, y_max * 1.25) # Start at 0, leave headroom for annotation
        
        # 2x font sizes for Academic Output
        plt.title(f'TVERC AVALANCHE SEARCH: Single Calibration\n'
                  f'Object: Cygnus X-1, Window: +{on_offset_min} to +{on_offset_max} min', 
                  fontsize=28, fontweight='bold', pad=25)
        plt.xlabel('Frequency (Hz)', fontsize=24)
        plt.ylabel(r'Coherence $\gamma^2(f)$', fontsize=24)
        plt.xticks(fontsize=20)
        plt.yticks(fontsize=20)
        
        plt.grid(True, which='both', linestyle=':', alpha=0.5)
        plt.legend(loc='upper right', fontsize=20)
        plt.tight_layout()
        
        # Memory management
        del freqs_off, bg_spectrum, freqs_on, flare_spectrum, plot_signal
        gc.collect()
        
        plt.show()
    else:
        print("\nCRITICAL ERROR: Analysis aborted due to missing LIGO data segments.")

run_avalanche_search()
        
