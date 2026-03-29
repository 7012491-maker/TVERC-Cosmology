# Install the necessary libraries for gravitational wave data analysis
!pip install -q gwpy lalsuite

import numpy as np
import matplotlib.pyplot as plt
from gwpy.timeseries import TimeSeries
import gc
import warnings

# Suppress minor warnings for a clean academic output
warnings.filterwarnings('ignore')

print("Libraries imported successfully. Ready for TVERC Evolution Search.")

# =====================================================================
# EVOLUTION SEARCH CONFIGURATION (Targeting Viscous Time Lag: V404 Cygni)
# =====================================================================
flare_gps = 1243771218   # GPS time of the detected X-ray flare
duration = 300           # Duration of each analysis window (seconds)

# Delay array in minutes: scanning from 0 to 80 minutes post-flare
delays_minutes = list(range(0, 85, 5))

# Target frequency window (around the detected 1780 Hz peak)
f_target_min = 1778
f_target_max = 1782

def run_evolution_search():
    print(f"\n--- LAUNCHING TVERC EVOLUTION SWEEP: V404 CYGNI (V4.1 - Strict DSP) ---")
    print(f"Scanning hum power in the band: {f_target_min}-{f_target_max} Hz")
    
    valid_delays = []
    hum_energies = []

    for lag in delays_minutes:
        start = flare_gps + (lag * 60)
        end = start + duration
        print(f"[ANALYSIS] Lag: +{lag:3} min | GPS: {start}")
        
        try:
            # Fetching RAW data from Hanford and Livingston
            h1 = TimeSeries.fetch_open_data('H1', start, end, cache=True)
            l1 = TimeSeries.fetch_open_data('L1', start, end, cache=True)

            if h1 is None or l1 is None: 
                print(f"  -> Detectors offline or data missing, skipping.")
                continue

            # CRITICAL FIX: Direct coherence calculation on RAW strain data.
            # No whitening applied to preserve true phase evolution over time.
            coh = h1.coherence(l1, fftlength=4, overlap=2)
            
            f_vals = coh.frequencies.value
            c_vals = coh.value

            # Filtering for the TVERC target frequency window
            mask = (f_vals >= f_target_min) & (f_vals <= f_target_max)
            c_target = c_vals[mask]

            # Safe mean calculation (ignoring potential NaNs from missing data segments)
            valid_c_target = c_target[~np.isnan(c_target)]
            
            if len(valid_c_target) > 0:
                mean_power = np.mean(valid_c_target)
                
                valid_delays.append(lag)
                hum_energies.append(mean_power)
                print(f"  -> Mean Hum Amplitude: {mean_power:.6f}")
            else:
                print(f"  -> No valid data in frequency band, skipping.")

            # Memory cleanup
            del h1, l1, coh
            gc.collect()

        except Exception as e:
            print(f"  -> Loading Error: {e}")

    # =====================================================================
    # GENERATING THE EVOLUTION PLOT (ACADEMIC STYLE)
    # =====================================================================
    if len(valid_delays) > 1:
        print("\nGENERATING TVERC VISCOUS INFALL CURVE...")
        
        # Large figsize for 2x fonts
        plt.figure(figsize=(20, 12))
        
        # Plotting the evolution line (Dark Red style applied)
        plt.plot(valid_delays, hum_energies, marker='o', markersize=12, 
                 color='darkred', lw=4, label='Raw Acoustic Hum Power')
        
        # Visual shading to highlight energy levels (Red style applied)
        plt.fill_between(valid_delays, hum_energies, np.min(hum_energies)*0.95, 
                         color='red', alpha=0.1)

        # 2x Font sizes for main elements
        plt.title('TVERC TWILIGHT HUM TIME EVOLUTION (V404 Cygni)\n'
                  'Demonstration of Fast Infall & Vacuum Optical Viscosity', 
                  fontsize=28, fontweight='bold', pad=30)
        
        plt.xlabel('Time Post X-ray Flare (Minutes)', fontsize=24, labelpad=15)
        plt.ylabel(f'Coherence Amplitude ({f_target_min}-{f_target_max} Hz)', 
                   fontsize=24, labelpad=15)
        
        # Axis scaling and ticks
        plt.ylim(np.min(hum_energies) * 0.98, np.max(hum_energies) * 1.05)
        plt.xticks(valid_delays, fontsize=18)
        plt.yticks(fontsize=18)
        
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.legend(fontsize=20, loc='upper right')
        plt.tight_layout()
        plt.show()
    else:
        print("\nCRITICAL ERROR: Insufficient data collected (LIGO servers did not return segments).")

run_evolution_search()
