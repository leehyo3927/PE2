import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import find_peaks, savgol_filter
from data_parser import parse_wafer_data  # 💡 공통 파서 모듈 불러오기

# ==========================================================
# USER SETTING & CONFIGURATION
# ==========================================================
zip_path = "../dat/HY202103.zip"
base_save_dir = "../res/WaferMap_BoxPlot(VpiL)"
os.makedirs(base_save_dir, exist_ok=True)

target_wafers = ['D07', 'D08', 'D23', 'D24']
L_length = 0.05  # phase shifter length [cm]

# ✨ 밴드별 VpiL 타겟값 설정 (LMZO: O-band, LMZC: C-band)
TARGET_VPIL = {
    'LMZO': 1.4,
    'LMZC': 2.0
}

print("🚀 Stable Phase Tracking 기반 VpiL 통합 분석을 시작합니다...")

summary_rows = []
count = 0


# ==========================================================
# HELPER FUNCTION
# ==========================================================
def quadratic_subpixel(x, y):
    """valley 주변 3점으로 subpixel 위치 정밀 보정"""
    if len(x) < 3: return x[np.argmin(y)]
    idx = np.argmin(y)
    if idx == 0 or idx == len(x) - 1: return x[idx]
    xs = x[idx - 1:idx + 2]
    ys = y[idx - 1:idx + 2]
    c = np.polyfit(xs, ys, 2)
    if abs(c[0]) < 1e-12: return x[idx]
    return -c[1] / (2 * c[0])


# ==========================================================
# [Step 1] 데이터 파싱 및 VpiL 정밀 계산 (Phase Tracking)
# ==========================================================
for d in parse_wafer_data(zip_path, target_wafers):
    # REF baseline fitting
    m = (d['ref_data']['wl'] >= d['wl_min']) & (d['ref_data']['wl'] <= d['wl_max'])
    ref_w, ref_i = d['ref_data']['wl'][m], d['ref_data']['il'][m]
    if len(ref_w) < 31: continue

    ref_i = savgol_filter(ref_i, 31, 3)
    poly_func = np.poly1d(np.polyfit(ref_w, ref_i, 3))

    # Bias 데이터 유효성 검사
    valid_biases = [b for b in d['bias_data_list'] if b['bias'] is not None]
    if not valid_biases: continue

    # 0V 데이터 찾기
    z_data = next((b for b in valid_biases if b['bias'] == 0.0), None)
    if not z_data: continue

    # 1. FSR 계산 (가장 낮은 전압 기준)
    min_bias_data = min(valid_biases, key=lambda x: x['bias'])
    m_min = (min_bias_data['wl'] >= d['wl_min']) & (min_bias_data['wl'] <= d['wl_max'])
    w_min, i_min = min_bias_data['wl'][m_min], min_bias_data['il'][m_min]

    flat_min = savgol_filter(i_min, 31, 3) - poly_func(w_min)
    valleys, _ = find_peaks(-flat_min, prominence=0.3, distance=20)
    if len(valleys) < 2: continue
    fsr = np.mean(np.diff(w_min[valleys]))

    # 2. 0V 기준 valley 고정
    m0 = (z_data['wl'] >= d['wl_min']) & (z_data['wl'] <= d['wl_max'])
    w0, i0 = z_data['wl'][m0], z_data['il'][m0]

    flat0 = savgol_filter(i0, 31, 3) - poly_func(w0)
    valleys0, _ = find_peaks(-flat0, prominence=0.3, distance=20)
    if len(valleys0) == 0: continue
    nearest = np.argmin(np.abs(w0[valleys0] - d['target_wl']))
    center_wl = w0[valleys0[nearest]]

    # 3. 모든 bias에서 같은 valley 추적
    volts, phase_pi = [], []
    search_half = fsr / 2.5

    for b in sorted(valid_biases, key=lambda x: x['bias']):
        w, i = b['wl'], b['il']
        mb = (w >= d['wl_min']) & (w <= d['wl_max'])
        w, i = w[mb], i[mb]
        if len(w) < 31: continue

        local = (w >= center_wl - search_half) & (w <= center_wl + search_half)
        if np.sum(local) < 5: continue

        flat = savgol_filter(i[local], 11, 3) - poly_func(w[local])
        valley_wl = quadratic_subpixel(w[local], flat)
        phi = 2.0 * (valley_wl - center_wl) / fsr
        volts.append(b['bias'])
        phase_pi.append(phi)

    if len(volts) < 5: continue
    volts, phase_pi = np.array(volts), np.array(phase_pi)

    # 4. 2차 fitting & 미분을 통한 VpiL 계산
    fit_func = np.poly1d(np.polyfit(volts, phase_pi, 2))
    dfunc = np.polyder(fit_func)

    slope = np.abs(dfunc(volts))
    slope = np.where(slope < 1e-5, 1e-5, slope)
    vpil = L_length / slope

    # 💡 물리적으로 유효한 범위(0.1 ~ 10.0)의 값만 필터링
    good = (vpil >= 0.1) & (vpil <= 10.0)
    if np.sum(good) == 0: continue

    summary_rows.append({
        "Wafer": d['wafer_id'], "Band": d['band'],
        "Column": d['die_c'], "Row": d['die_r'],
        "Radius": np.sqrt(d['die_c'] ** 2 + d['die_r'] ** 2),
        "VpiL": np.mean(vpil[good])
    })

    count += 1
    if count % 100 == 0:
        print(f"현재 {count}개 Die 파싱 및 VpiL 분석 완료...")

# ==========================================================
# [Step 2] 데이터 정리 및 통계 필터링
# ==========================================================
if not summary_rows:
    print("❌ 유효한 데이터를 찾지 못했습니다.")
    exit()

df = pd.DataFrame(summary_rows)
filtered_df = pd.DataFrame()

# 동일 좌표 평균화
df_grouped = df.groupby(['Wafer', 'Band', 'Column', 'Row', 'Radius'], as_index=False)['VpiL'].mean()

# 3-Sigma 아웃라이어 최종 제거
for (wafer, band), group in df_grouped.groupby(['Wafer', 'Band']):
    if len(group) > 5:
        m, s = group['VpiL'].mean(), group['VpiL'].std()
        valid_group = group[(group['VpiL'] >= m - 3 * s) & (group['VpiL'] <= m + 3 * s)]
        filtered_df = pd.concat([filtered_df, valid_group])
    else:
        filtered_df = pd.concat([filtered_df, group])

max_r = filtered_df['Radius'].max()
edge_limit = max_r * 0.75
filtered_df['Region'] = np.where(filtered_df['Radius'] > edge_limit, 'Edge', 'Center')

print(f"\n✅ 에러 데이터 제거 완료! 총 {len(filtered_df)}개의 유효 다이를 기반으로 시각화를 진행합니다.")

# ==========================================================
# [Step 3] Wafer Map 시각화
# ==========================================================
band_limits = {}
for b in filtered_df['Band'].unique():
    b_data = filtered_df[filtered_df['Band'] == b]['VpiL']
    band_limits[b] = {'min': b_data.min() - 0.05, 'max': b_data.max() + 0.05}

for (wafer, band), group in filtered_df.groupby(['Wafer', 'Band']):
    plt.figure(figsize=(9, 9))
    theta = np.linspace(0, 2 * np.pi, 100)
    plt.plot((max_r + 0.5) * np.cos(theta), (max_r + 0.5) * np.sin(theta), color='gray', lw=2)
    plt.plot(edge_limit * np.cos(theta), edge_limit * np.sin(theta), 'r--', lw=2, alpha=0.6,
             label='Center/Edge Boundary')

    v_min, v_max = band_limits[band]['min'], band_limits[band]['max']

    scatter = plt.scatter(group['Column'], group['Row'], c=group['VpiL'], cmap='coolwarm',
                          vmin=v_min, vmax=v_max, s=600, edgecolor='black', alpha=0.9, zorder=5)

    for _, row in group.iterrows():
        plt.text(row['Column'], row['Row'], f"{row['VpiL']:.2f}",
                 ha='center', va='center', fontsize=10, weight='bold', color='black', zorder=10)

    cbar = plt.colorbar(scatter, shrink=0.8)
    cbar.set_label('Avg Vpi*L [V*cm]', fontsize=14, fontweight='bold')
    cbar.ax.tick_params(labelsize=12)
    for l in cbar.ax.yaxis.get_ticklabels(): l.set_weight("bold")

    plt.title(f"Wafer Map: {wafer} / {band}\nNormalized Avg VpiL ({v_min:.2f} ~ {v_max:.2f} V*cm)", fontsize=18,
              fontweight='bold', pad=15)
    plt.xlabel("Die Column", fontsize=16, fontweight='bold')
    plt.ylabel("Die Row", fontsize=16, fontweight='bold')
    plt.xticks(fontsize=12, fontweight='bold');
    plt.yticks(fontsize=12, fontweight='bold')
    plt.gca().set_aspect('equal')
    plt.legend(loc='upper right', prop={'size': 12, 'weight': 'bold'})
    plt.grid(True, alpha=0.3, linestyle=':')

    save_path = os.path.join(base_save_dir, f"Map_{wafer}_{band}_AvgVpiL.png")
    plt.savefig(save_path, bbox_inches='tight')
    plt.close()

# ==========================================================
# [Step 4] Box Plot 분석 (전체 및 지역별)
# ==========================================================
flierprops = dict(marker='d', markerfacecolor='black', markersize=6, markeredgecolor='black', alpha=0.6)

for band in filtered_df['Band'].unique():
    band_df = filtered_df[filtered_df['Band'] == band]
    wafer_list = sorted(band_df['Wafer'].unique())
    current_target = TARGET_VPIL.get(band, 1.5)

    # ----------------------------------------------------
    # 1. Overall Wafer Comparison
    # ----------------------------------------------------
    plt.figure(figsize=(12, 7))
    box_data = [band_df[band_df['Wafer'] == w]['VpiL'].values for w in wafer_list]
    positions_overall = range(1, len(wafer_list) + 1)

    box = plt.boxplot(box_data, positions=positions_overall, tick_labels=wafer_list, patch_artist=True,
                      flierprops=flierprops)
    for patch in box['boxes']:
        patch.set_facecolor('skyblue')
        patch.set_alpha(0.6)

    for pos, data in zip(positions_overall, box_data):
        x_jitter = np.random.normal(pos, 0.05, size=len(data))
        plt.scatter(x_jitter, data, color='black', alpha=0.5, s=20, zorder=3)

    plt.axhline(current_target, color='red', ls='-', linewidth=2.5, label=f'Target ({current_target} V*cm)')
    plt.text(0.5, current_target + 0.05, f"Target: {current_target} V*cm", color='red', fontweight='bold', fontsize=13)

    plt.title(f"Avg Vpi*L Distribution by Wafer: {band}", fontsize=18, fontweight='bold', pad=15)
    plt.ylabel("Avg Vpi*L [V*cm]", fontsize=16, fontweight='bold', labelpad=10)
    plt.xticks(fontsize=14, fontweight='bold');
    plt.yticks(fontsize=14, fontweight='bold')
    plt.legend(loc='upper right', prop={'size': 13, 'weight': 'bold'})
    plt.grid(True, axis='y', alpha=0.5, linestyle=':')
    plt.tight_layout()
    plt.savefig(os.path.join(base_save_dir, f"Box_Overall_{band}_AvgVpiL.png"))
    plt.close()

    # ----------------------------------------------------
    # 2. Center vs Edge Analysis
    # ----------------------------------------------------
    plt.figure(figsize=(14, 8))
    positions, plot_data, labels, colors = [], [], [], []

    for i, wafer in enumerate(wafer_list):
        w_df = band_df[band_df['Wafer'] == wafer]
        c_data = w_df[w_df['Region'] == 'Center']['VpiL'].values
        e_data = w_df[w_df['Region'] == 'Edge']['VpiL'].values

        if len(c_data) > 0:
            plot_data.append(c_data);
            positions.append(i * 3 + 1)
            labels.append(f"{wafer}\n(C)\nn={len(c_data)}");
            colors.append('#3498db')
        if len(e_data) > 0:
            plot_data.append(e_data);
            positions.append(i * 3 + 2)
            labels.append(f"{wafer}\n(E)\nn={len(e_data)}");
            colors.append('#e74c3c')

    if not plot_data: continue

    box_reg = plt.boxplot(plot_data, positions=positions, tick_labels=labels, patch_artist=True, flierprops=flierprops)
    for patch, color in zip(box_reg['boxes'], colors):
        patch.set_facecolor(color);
        patch.set_alpha(0.6)

    for pos, data in zip(positions, plot_data):
        x_jitter = np.random.normal(pos, 0.05, size=len(data))
        plt.scatter(x_jitter, data, color='black', alpha=0.5, s=20, zorder=3)

    plt.axhline(current_target, color='red', ls='-', linewidth=2.5, label=f'Target ({current_target} V*cm)')
    plt.text(0.5, current_target + 0.05, f"Target: {current_target} V*cm", color='red', fontweight='bold', fontsize=13)

    plt.title(f"Center vs Edge Avg Vpi*L Analysis: {band}", fontsize=18, fontweight='bold', pad=15)
    plt.xlabel('Wafer ID & Region (C: Center, E: Edge)', fontsize=16, fontweight='bold', labelpad=10)
    plt.ylabel("Avg Vpi*L [V*cm]", fontsize=16, fontweight='bold', labelpad=10)
    plt.xticks(positions, labels, fontsize=13, fontweight='bold');
    plt.yticks(fontsize=14, fontweight='bold')
    plt.legend(loc='upper right', prop={'size': 13, 'weight': 'bold'})
    plt.grid(True, axis='y', alpha=0.5, linestyle=':')
    plt.xlim(0, max(positions) + 1)
    plt.tight_layout()

    plt.savefig(os.path.join(base_save_dir, f"Box_Region_{band}_AvgVpiL.png"))
    plt.close()

print(f"✅ 모든 분석이 완료되었습니다. 시각화 개선이 적용된 결과 파일이 저장되었습니다.")