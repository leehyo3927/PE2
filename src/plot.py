import os
import matplotlib.pyplot as plt
from data_parser import parse_wafer_data

zip_path = "../dat/HY202103.zip"
base_save_dir = "../res/plots"
target_wafers = ['D07', 'D08', 'D23', 'D24']

for d in parse_wafer_data(zip_path, target_wafers):
    plt.figure(figsize=(10, 6))
    for b in d['bias_data_list']: plt.plot(b['wl'], b['il'], label=b['label'])
    plt.plot(d['ref_data']['wl'], d['ref_data']['il'], label=d['ref_data']['label'])

    plt.title(f"Wafer: {d['wafer_id']} / Coord: ({d['die_c']}, {d['die_r']}) / Band: {d['band']}")
    plt.ylim(-65, 5); plt.xlabel("Wavelength (nm)"); plt.ylabel("IL (dB)")
    plt.legend(loc='best'); plt.grid(True)

    w_dir = os.path.join(base_save_dir, d['wafer_id'])
    os.makedirs(w_dir, exist_ok=True)
    plt.savefig(os.path.join(w_dir, f"{d['wafer_id']}_C{d['die_c']}_R{d['die_r']}_{d['band']}.png"))
    plt.close()
print("✅ 플롯 저장 완료")