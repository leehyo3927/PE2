import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from data_parser import parse_wafer_data

zip_path = "../dat/HY202103"
base_res_dir = "../res/png"
target_wafers = ['D07', 'D08', 'D23', 'D24']
IL_TARGETS = {'LMZO': -8.75, 'LMZC': -8.75}

global_analysis_dir = os.path.join(base_res_dir, "Analysis")
os.makedirs(global_analysis_dir, exist_ok=True)

print("🚀 IL 추출 및 날짜별/Center vs Edge 통합 분석을 시작합니다...")

il_data_list = []
for d in parse_wafer_data(zip_path, target_wafers):
    date_str = d.get('date', 'Unknown_Date')

    max_peak = -999.0
    for b in d['bias_data_list']:
        if b['bias'] is None: continue
        m = (b['wl'] >= d['wl_min']) & (b['wl'] <= d['wl_max'])
        if np.any(m): max_peak = max(max_peak, np.max(b['il'][m]))

    if max_peak != -999.0:
        il_data_list.append(
            {'Wafer': d['wafer_id'], 'Band': d['band'], 'Date': date_str, 'Column': d['die_c'], 'Row': d['die_r'],
             'IL': max_peak})

df = pd.DataFrame(il_data_list).groupby(['Wafer', 'Band', 'Date', 'Column', 'Row'], as_index=False)['IL'].mean()
df['Radius'] = np.sqrt(df['Column'] ** 2 + df['Row'] ** 2)

filtered_df = pd.DataFrame()
for _, group in df.groupby(['Wafer', 'Band', 'Date']):
    m, s = group['IL'].mean(), group['IL'].std()
    filtered_df = pd.concat([filtered_df, group[(group['IL'] >= m - 3 * s) & (group['IL'] <= m + 3 * s)]])

max_rad = filtered_df['Radius'].max()
filtered_df['Region'] = np.where(filtered_df['Radius'] > max_rad * 0.75, 'Edge', 'Center')

# ==========================================================
# [통일된 디자인] Wafer Map 그리기
# ==========================================================
for b in filtered_df['Band'].unique():
    limits = {'min': np.floor(filtered_df[filtered_df['Band'] == b]['IL'].min()),
              'max': np.ceil(filtered_df[filtered_df['Band'] == b]['IL'].max())}

    for (w, date), grp in filtered_df[filtered_df['Band'] == b].groupby(['Wafer', 'Date']):
        if grp.empty: continue

        plt.figure(figsize=(9, 9))
        th = np.linspace(0, 2 * np.pi, 100)
        plt.plot((max_rad + 0.5) * np.cos(th), (max_rad + 0.5) * np.sin(th), color='gray', lw=2)
        plt.plot(max_rad * 0.75 * np.cos(th), max_rad * 0.75 * np.sin(th), color='red', ls='--', lw=2, alpha=0.6)

        sc = plt.scatter(grp['Column'], grp['Row'], c=grp['IL'], cmap='coolwarm_r', vmin=limits['min'],
                         vmax=limits['max'], s=500, edgecolor='black', alpha=0.9, zorder=5)

        for _, r in grp.iterrows():
            plt.text(r['Column'], r['Row'], f"{r['IL']:.1f}", ha='center', va='center',
                     fontsize=10, fontweight='bold', color='black', zorder=10)

        cb = plt.colorbar(sc, shrink=0.8)
        cb.set_label('IL [dB]', fontsize=14, fontweight='bold')
        cb.ax.tick_params(labelsize=12)
        for l in cb.ax.yaxis.get_ticklabels(): l.set_weight("bold")

        plt.title(f"Wafer Map: {w} / {b} (IL)\nDate: {date}", fontsize=18, fontweight='bold', pad=15)
        plt.axis('off')  # 군더더기 축/격자 제거
        plt.gca().set_aspect('equal')

        w_dir = os.path.join(global_analysis_dir, w, date)
        os.makedirs(w_dir, exist_ok=True)
        plt.savefig(os.path.join(w_dir, f"Map_{w}_{b}_{date}_IL.png"), bbox_inches='tight')
        plt.close()

# ==========================================================
# [통일된 디자인] Box Plot 그리기
# ==========================================================
for b in ['LMZO', 'LMZC']:
    b_df = filtered_df[filtered_df['Band'] == b]
    if b_df.empty: continue

    for date, date_df in b_df.groupby('Date'):
        plt.figure(figsize=(14, 8))
        pos, data, lbl, clr = [], [], [], []

        for i, w in enumerate(sorted(date_df['Wafer'].unique())):
            w_df = date_df[date_df['Wafer'] == w]
            c, e = w_df[w_df['Region'] == 'Center']['IL'].values, w_df[w_df['Region'] == 'Edge']['IL'].values
            if len(c) > 0: pos.append(i * 3 + 1); data.append(c); lbl.append(f"{w}\n(C)\nn={len(c)}"); clr.append(
                '#3498db')
            if len(e) > 0: pos.append(i * 3 + 2); data.append(e); lbl.append(f"{w}\n(E)\nn={len(e)}"); clr.append(
                '#e74c3c')

        if not data: continue

        box = plt.boxplot(data, positions=pos, patch_artist=True,
                          flierprops=dict(marker='d', markerfacecolor='black', markersize=6, alpha=0.6))
        for p, c_hex in zip(box['boxes'], clr): p.set_facecolor(c_hex); p.set_alpha(0.6)

        # Jitter(산점도) 추가
        for p, d_arr in zip(pos, data):
            plt.scatter(np.random.normal(p, 0.05, len(d_arr)), d_arr, color='black', alpha=0.5, s=20, zorder=3)

        avg_il, tgt_il = date_df['IL'].mean(), IL_TARGETS.get(b, -8.75)
        plt.axhline(avg_il, color='blue', ls='--', lw=2.5, label=f'Avg: {avg_il:.2f} dB')
        plt.axhline(tgt_il, color='red', ls='-', lw=2.5, label=f'Target: {tgt_il:.2f} dB')

        plt.title(f"IL Analysis ({b}) : Center vs Edge\nDate: {date}", fontsize=18, fontweight='bold', pad=15)
        plt.xticks(pos, lbl, fontsize=13, fontweight='bold')
        plt.yticks(fontsize=14, fontweight='bold')
        plt.ylabel('IL [dB]', fontsize=16, fontweight='bold')
        plt.legend(loc='upper right', prop={'size': 13, 'weight': 'bold'})
        plt.grid(True, axis='y', ls=':', alpha=0.6)
        plt.xlim(0, max(pos) + 1)
        plt.tight_layout()

        box_dir = os.path.join(global_analysis_dir, "Overall_BoxPlots", date)
        os.makedirs(box_dir, exist_ok=True)
        plt.savefig(os.path.join(box_dir, f"Box_{b}_{date}_IL.png"), bbox_inches='tight')
        plt.close()

print("✅ 날짜별 IL 분석 결과(Wafer Map, Box Plot) 저장이 완료되었습니다!")