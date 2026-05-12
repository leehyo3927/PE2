import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from data_parser import parse_wafer_data

zip_path = "../dat/HY202103.zip"
save_grp = "../res/VpiL - voltage"
save_box = "../res/WaferMap_BoxPlot(VpiL)_Advanced"
os.makedirs(save_grp, exist_ok=True);
os.makedirs(save_box, exist_ok=True)

target_wafers = ['D07', 'D08', 'D23', 'D24']
L_length, TARGET_VPIL = 0.05, {'LMZO': 1.4, 'LMZC': 2.0}
summary_rows = []


def q_sub(x, y):
    if len(x) < 3: return x[np.argmin(y)]
    idx = np.argmin(y)
    if idx == 0 or idx == len(x) - 1: return x[idx]
    c = np.polyfit(x[idx - 1:idx + 2], y[idx - 1:idx + 2], 2)
    return -c[1] / (2 * c[0]) if abs(c[0]) > 1e-12 else x[idx]


for d in parse_wafer_data(zip_path, target_wafers):
    m = (d['ref_data']['wl'] >= d['wl_min']) & (d['ref_data']['wl'] <= d['wl_max'])
    v_ref_wl, v_ref_il = d['ref_data']['wl'][m], d['ref_data']['il'][m]
    if len(v_ref_wl) < 31: continue
    poly_func = np.poly1d(np.polyfit(v_ref_wl, savgol_filter(v_ref_il, 31, 3), 3))

    z_data = next((b for b in d['bias_data_list'] if b['bias'] == 0.0), None)
    if not z_data: continue

    m0 = (z_data['wl'] >= d['wl_min']) & (z_data['wl'] <= d['wl_max'])
    w0, i0 = z_data['wl'][m0], z_data['il'][m0]
    flat0 = savgol_filter(i0, 31, 3) - poly_func(w0)
    v0, _ = find_peaks(-flat0, prominence=0.3, distance=20)
    if len(v0) < 2: continue

    fsr = np.mean(np.diff(w0[v0]))
    cwl = w0[v0[np.argmin(np.abs(w0[v0] - d['target_wl']))]]

    volts, p_pi = [], []
    sh = fsr / 2.5
    for b in d['bias_data_list']:
        if b['bias'] is None: continue
        w, i = b['wl'], b['il']
        mb = (w >= d['wl_min']) & (w <= d['wl_max'])
        wb, ib = w[mb], i[mb]

        mloc = (wb >= cwl - sh) & (wb <= cwl + sh)
        if np.sum(mloc) < 5: continue

        flat = savgol_filter(ib[mloc], 11, 3) - poly_func(wb[mloc])
        vwl = q_sub(wb[mloc], flat)
        volts.append(b['bias']);
        p_pi.append(2.0 * (vwl - cwl) / fsr)

    if len(volts) < 5: continue
    volts, p_pi = np.array(volts), np.array(p_pi)
    fit = np.poly1d(np.polyfit(volts, p_pi, 2))

    vpil = L_length / np.where(np.abs(np.polyder(fit)(volts)) < 1e-5, 1e-5, np.abs(np.polyder(fit)(volts)))
    good = (vpil >= 0.1) & (vpil <= 10.0)
    if np.sum(good) == 0: continue

    avg_v = np.mean(vpil[good])
    summary_rows.append({'Wafer': d['wafer_id'], 'Band': d['band'], 'Column': d['die_c'], 'Row': d['die_r'],
                         'Radius': np.sqrt(d['die_c'] ** 2 + d['die_r'] ** 2), 'VpiL': avg_v})

    # 그래프
    plt.figure(figsize=(8, 6))
    plt.plot(volts[good], vpil[good], 's-', lw=2, label="Measured")
    xfit = np.linspace(volts.min(), volts.max(), 200)
    vpil_f = L_length / np.where(np.abs(np.polyder(fit)(xfit)) < 1e-5, 1e-5, np.abs(np.polyder(fit)(xfit)))
    plt.plot(xfit, vpil_f, '--', alpha=0.7, label="Trend")
    plt.axhline(avg_v, ls=':', label=f'Avg={avg_v:.3f}')
    plt.title(f"{d['wafer_id']} {d['band']} VπL");
    plt.grid(True);
    plt.legend()
    w_dir = os.path.join(save_grp, d['wafer_id']);
    os.makedirs(w_dir, exist_ok=True)
    plt.savefig(os.path.join(w_dir, f"{d['wafer_id']}_C{d['die_c']}_R{d['die_r']}_VpiL.png"));
    plt.close()

df = pd.DataFrame(summary_rows)
if not df.empty:
    df.to_csv(os.path.join(save_grp, "Summary_VpiL.csv"), index=False)
    filtered = pd.DataFrame()
    for _, g in df.groupby(['Wafer', 'Band']):
        m, s = g['VpiL'].mean(), g['VpiL'].std()
        filtered = pd.concat([filtered, g[(g['VpiL'] >= m - 3 * s) & (g['VpiL'] <= m + 3 * s)]])

    filtered['Region'] = np.where(filtered['Radius'] > filtered['Radius'].max() * 0.75, 'Edge', 'Center')

    for b in ['LMZO', 'LMZC']:
        b_df = filtered[filtered['Band'] == b]
        if b_df.empty: continue

        plt.figure(figsize=(14, 8))
        pos, data, lbl, clr = [], [], [], []
        for i, w in enumerate(sorted(b_df['Wafer'].unique())):
            c, e = b_df[(b_df['Wafer'] == w) & (b_df['Region'] == 'Center')]['VpiL'].values, \
            b_df[(b_df['Wafer'] == w) & (b_df['Region'] == 'Edge')]['VpiL'].values
            if len(c) > 0: pos.append(i * 3 + 1); data.append(c); lbl.append(f"{w}\n(C)"); clr.append('#3498db')
            if len(e) > 0: pos.append(i * 3 + 2); data.append(e); lbl.append(f"{w}\n(E)"); clr.append('#e74c3c')

        bx = plt.boxplot(data, positions=pos, patch_artist=True)
        for p, c in zip(bx['boxes'], clr): p.set_facecolor(c); p.set_alpha(0.6)

        plt.axhline(TARGET_VPIL[b], color='red', ls='-', lw=2.5)
        plt.axhline(b_df['VpiL'].mean(), color='blue', ls='--', lw=2.5)
        plt.xticks(pos, lbl, fontweight='bold');
        plt.title(f"VpiL Analysis ({b})", fontweight='bold', fontsize=18)
        plt.tight_layout();
        plt.savefig(os.path.join(save_box, f"Box_{b}_VpiL.png"));
        plt.close()
print("✅ VpiL 통합 분석 완료")