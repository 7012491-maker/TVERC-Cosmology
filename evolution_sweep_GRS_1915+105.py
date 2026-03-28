# Install the necessary libraries for gravitational wave data analysis
!pip install -q gwpy
!pip install -q lalsuite

import numpy as np
import matplotlib.pyplot as plt
from gwpy.timeseries import TimeSeries
import gc
import warnings

# Suppress minor warnings for a clean academic output
warnings.filterwarnings('ignore')

print("Libraries imported successfully. Ready for TVERC Evolution Search.")

# =====================================================================
# EVOLUTION SEARCH CONFIGURATION (Targeting Viscous Time Lag: GRS 1915+105)
# =====================================================================
flare_gps = 1240228818   # GPS time of the detected X-ray flare
duration = 300           # Duration of each analysis window (seconds)

# Delay array in minutes: scanning from 0 to 120 minutes post-flare
delays_minutes = list(range(0, 120, 5))

# Target frequency window (around the detected 1339 Hz peak)
f_target_min = 1330
f_target_max = 1350

def run_evolution_search():
    print(f"\n--- LAUNCHING TVERC EVOLUTION SWEEP: GRS 1915+105 (V4.0) ---")
    print(f"Scanning hum power in the band: {f_target_min}-{f_target_max} Hz")
    
    valid_delays = []
    hum_energies = []

    for lag in delays_minutes:
        start = flare_gps + (lag * 60)
        end = start + duration
        print(f"[ANALYSIS] Lag: +{lag:3} min | GPS: {start}")
        
        try:
            # Fetching raw data from Hanford and Livingston
            h1 = TimeSeries.fetch_open_data('H1', start, end, cache=True)
            l1 = TimeSeries.fetch_open_data('L1', start, end, cache=True)

            if h1 is None or l1 is None: 
                print(f"  -> Detectors offline or data missing, skipping.")
                continue

            # Whitening to normalize the spectral floor
            h1_w = h1.whiten()
            l1_w = l1.whiten()

            # High-resolution cross-detector coherence
            coh = h1_w.coherence(l1_w, fftlength=4, overlap=2)
            
            f_vals = coh.frequencies.value
            c_vals = np.nan_to_num(coh.value)

            # Filtering for the TVERC target frequency window
            mask = (f_vals >= f_target_min) & (f_vals <= f_target_max)
            c_target = c_vals[mask]

            # Calculate mean coherence (Hum Power) for this temporal window
            mean_power = np.mean(c_target)
            
            valid_delays.append(lag)
            hum_energies.append(mean_power)
            print(f"  -> Mean Hum Amplitude: {mean_power:.6f}")

            # Memory cleanup
            del h1, l1, h1_w, l1_w, coh
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
        
        # Plotting the evolution line (Markers kept as simple circles)
        plt.plot(valid_delays, hum_energies, marker='o', markersize=12, 
                 color='darkred', lw=4, label='Twilight Hum Power')
        
        # Visual shading to highlight energy levels
        plt.fill_between(valid_delays, hum_energies, np.min(hum_energies)*0.95, 
                         color='red', alpha=0.1)

        # 2x Font sizes for main elements
        plt.title('TVERC TWILIGHT HUM TIME EVOLUTION (GRS 1915+105)\n'
                  'Demonstration of Vacuum Optical Viscosity', 
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
