import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from data_parser import parse_wafer_data

zip_path = "../dat/HY202103.zip"
base_save_dir = "../res/Faltting"
target_wafers = ['D07', 'D08', 'D23', 'D24']

for d in parse_wafer_data(zip_path, target_wafers):
    m = (d['ref_data']['wl'] >= d['wl_min']) & (d['ref_data']['wl'] <= d['wl_max'])
    v_ref_wl, v_ref_il = d['ref_data']['wl'][m], d['ref_data']['il'][m]
    if len(v_ref_wl) < 4: continue

    poly = np.poly1d(np.polyfit(v_ref_wl, v_ref_il, 3))

    plt.figure(figsize=(10, 6))
    plt.plot(v_ref_wl, v_ref_il - poly(v_ref_wl), label='REF', color='black', lw=2.5)

    for b in d['bias_data_list']:
        m_b = (b['wl'] >= d['wl_min']) & (b['wl'] <= d['wl_max'])
        v_wl, v_il = b['wl'][m_b], b['il'][m_b]
        if len(v_wl) == 0: continue

        flat_il = v_il - poly(v_wl)
        peaks, _ = find_peaks(flat_il, prominence=3.0, distance=30)
        if len(peaks) >= 2: flat_il -= np.poly1d(np.polyfit(v_wl[peaks], flat_il[peaks], 1))(v_wl)
        plt.plot(v_wl, flat_il, label=b['label'], alpha=0.8)

    plt.title(f"Wafer: {d['wafer_id']} / {d['band']} Flattened")
    plt.xlabel('Wavelength [nm]');
    plt.ylabel('Transmission [dB]')
    plt.axhline(0, color='gray', ls='--');
    plt.xlim(d['wl_min'], d['wl_max'])
    plt.legend(bbox_to_anchor=(1.25, 1.0));
    plt.grid(True, ls='--')

    w_dir = os.path.join(base_save_dir, d['wafer_id'])
    os.makedirs(w_dir, exist_ok=True)
    plt.savefig(os.path.join(w_dir, f"{d['wafer_id']}_C{d['die_c']}_R{d['die_r']}_Flat.png"), bbox_inches='tight')
    plt.close()
print("✅ 기본 평탄화 저장 완료")