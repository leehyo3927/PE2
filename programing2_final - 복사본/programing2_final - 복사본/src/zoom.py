import os
import numpy as np
import matplotlib.pyplot as plt
from scipy.signal import find_peaks
from data_parser import parse_wafer_data

zip_path = "../dat/HY202103.zip"
base_save_dir = "../res/zoom"
target_wafers = ['D07', 'D08', 'D23', 'D24']

for d in parse_wafer_data(zip_path, target_wafers):
    m = (d['ref_data']['wl'] >= d['wl_min']) & (d['ref_data']['wl'] <= d['wl_max'])
    v_ref_wl, v_ref_il = d['ref_data']['wl'][m], d['ref_data']['il'][m]
    if len(v_ref_wl) < 4: continue

    poly = np.poly1d(np.polyfit(v_ref_wl, v_ref_il, 3))
    z_min, z_max = d['wl_min'], d['wl_max']

    t_bias = next((b for b in d['bias_data_list'] if b['bias'] == -2.0),
                  d['bias_data_list'][0] if d['bias_data_list'] else None)
    if t_bias:
        mt = (t_bias['wl'] >= d['wl_min']) & (t_bias['wl'] <= d['wl_max'])
        wt, it = t_bias['wl'][mt], t_bias['il'][mt]
        peaks, _ = find_peaks(it - poly(wt), prominence=3.0, distance=30)
        if len(peaks) >= 2:
            cent = (wt[peaks[:-1]] + wt[peaks[1:]]) / 2.0
            idx = np.argmin(np.abs(cent - d['target_wl']))
            z_min, z_max = wt[peaks[idx]] - 0.5, wt[peaks[idx + 1]] + 0.5

    plt.figure(figsize=(10, 6))
    for b in d['bias_data_list']:
        mb = (b['wl'] >= d['wl_min']) & (b['wl'] <= d['wl_max'])
        wb, ib = b['wl'][mb], b['il'][mb]
        if len(wb) == 0: continue

        flat = ib - poly(wb)
        peaks, _ = find_peaks(flat, prominence=3.0, distance=30)
        if len(peaks) >= 2: flat -= np.poly1d(np.polyfit(wb[peaks], flat[peaks], 1))(wb)
        plt.plot(wb, flat, label=b['label'], alpha=0.8)

    plt.axhline(0, color='gray', ls='--');
    plt.xlim(z_min, z_max)
    plt.legend(bbox_to_anchor=(1.25, 1.0));
    plt.title(f"Zoom Only: {d['wafer_id']} {d['band']}")

    w_dir = os.path.join(base_save_dir, d['wafer_id']);
    os.makedirs(w_dir, exist_ok=True)
    plt.savefig(os.path.join(w_dir, f"{d['wafer_id']}_Zoom.png"), bbox_inches='tight');
    plt.close()
print("✅ 줌 전용 저장 완료")