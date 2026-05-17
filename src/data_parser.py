import zipfile
import xml.etree.ElementTree as ET
import numpy as np


def parse_wafer_data(zip_path, target_wafers):
    """Zip 파일을 열어 XML 데이터를 파싱하고 다이(Die)별 데이터를 반환합니다."""
    with zipfile.ZipFile(zip_path, 'r') as myzip:
        for file_name in myzip.namelist():
            if not file_name.lower().endswith('.xml'): continue
            if not any(w in file_name for w in target_wafers): continue

            with myzip.open(file_name) as f:
                try:
                    tree = ET.parse(f)
                    root = tree.getroot()
                    info = root.find('.//TestSiteInfo')
                    if info is None: continue

                    test_site = info.get('TestSite', '')
                    if 'LMZO' in test_site.upper():
                        band, wl_min, wl_max, tgt_wl = 'LMZO', 1260.0, 1360.0, 1310.0
                    elif 'LMZC' in test_site.upper():
                        band, wl_min, wl_max, tgt_wl = 'LMZC', 1520.0, 1580.0, 1550.0
                    else:
                        continue

                    die_c = int(info.get('DieRow', 0)) if info.get('DieRow') else 0
                    die_r = int(info.get('DieColumn', 0)) if info.get('DieColumn') else 0
                    wafer_id = next((w for w in target_wafers if w in file_name), "Unknown")

                    sweeps = root.findall('.//WavelengthSweep')
                    if not sweeps or len(sweeps) < 2: continue

                    ref_data = None
                    bias_list = []

                    for i, sweep in enumerate(sweeps):
                        l_elem, il_elem = sweep.find('L'), sweep.find('IL')
                        if l_elem is None or il_elem is None: continue

                        l_data = np.array(list(map(float, l_elem.text.split(','))))
                        il_data = np.array(list(map(float, il_elem.text.split(','))))
                        bias_str = sweep.get('DCBias', '')

                        if i == len(sweeps) - 1:
                            ref_data = {'wl': l_data, 'il': il_data, 'label': 'REF'}
                        else:
                            try:
                                bias_val = float(bias_str); label = f'{bias_val}V'
                            except:
                                bias_val = None; label = f'Bias: {bias_str}'
                            bias_list.append({'bias': bias_val, 'wl': l_data, 'il': il_data, 'label': label})

                    if ref_data is None: continue

                    yield {
                        'wafer_id': wafer_id, 'band': band, 'die_c': die_c, 'die_r': die_r,
                        'wl_min': wl_min, 'wl_max': wl_max, 'target_wl': tgt_wl,
                        'ref_data': ref_data, 'bias_data_list': bias_list
                    }
                except Exception as e:
                    print(f"[{file_name}] 파싱 에러: {e}")