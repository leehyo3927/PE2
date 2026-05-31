import os
import math
from PIL import Image


def get_sort_index(filename):
    """
    다이(Die) 분석 이미지의 정렬 순서를 결정합니다.
    1.Plot(Raw) -> 2.Flatting -> 3.Fitting -> 4.Zoom -> 5.Phase shift -> 6.VpiL
    """
    name = filename.lower()
    if 'raw' in name or 'plot' in name:
        return 1
    elif 'flatting' in name or 'flat' in name:
        return 2
    elif 'zoom' in name:
        return 3
    elif 'fitting' in name or 'fit' in name:
        return 4
    elif 'phase' in name:
        return 5
    elif 'vpil' in name:
        return 6
    else:
        return 99


def get_map_sort_index(filename):
    """
    웨이퍼 맵 및 박스 플롯 이미지의 정렬 순서를 결정합니다.
    요청하신 순서: 1.ER(소광비) -> 2.IL(손실) -> 3.VpiL(효율) 순서로 배치합니다.
    """
    name = filename.upper()
    if 'ER' in name:
        return 1
    elif 'IL' in name and 'VPIL' not in name:
        return 2
    elif 'VPIL' in name:
        return 3
    else:
        return 99


def merge_die_images(base_dir, delete_originals=True):
    """
    각 날짜 폴더 내의 분석 이미지들을 좌표(Die) 및 밴드(Band)별로 그룹화하여
    가로 3, 세로 2 격자 형태로 병합하고 원본을 삭제합니다.
    """
    print("▶ 1. 날짜 폴더 내 다이(Die) 분석 이미지 병합 및 원본 파일 관리를 시작합니다...")
    combine_count = 0
    deleted_count = 0

    for wafer in os.listdir(base_dir):
        wafer_path = os.path.join(base_dir, wafer)

        # 🌟 WaferMap, BoxPlot 등 시스템 폴더는 다이(Die) 병합에서 제외
        if not os.path.isdir(wafer_path) or wafer in ["Analysis", "WaferMap", "BoxPlot"]:
            continue

        for date_folder in os.listdir(wafer_path):
            date_path = os.path.join(wafer_path, date_folder)
            if not os.path.isdir(date_path):
                continue

            for f in os.listdir(date_path):
                if f.startswith('HY202103_') and 'LION1_DCM' in f and f.endswith('.png'):
                    try:
                        os.remove(os.path.join(date_path, f))
                    except:
                        pass

            image_files = [f for f in os.listdir(date_path) if f.endswith('.png')
                           and not f.startswith('Map_')
                           and not f.startswith('Box_')
                           and not f.startswith('HY202103_')]

            if not image_files:
                continue

            die_groups = {}
            for f in image_files:
                parts = f.replace(".png", "").split('_')
                if len(parts) >= 4:
                    try:
                        c_val = parts[1].replace('C', '')
                        r_val = parts[2].replace('R', '')
                        band = parts[3]
                        group_key = (c_val, r_val, band)

                        if group_key not in die_groups:
                            die_groups[group_key] = []
                        die_groups[group_key].append(f)
                    except Exception as e:
                        print(f"파일 이름 분석 오류: {f} -> {e}")

            for (c_val, r_val, band), files in die_groups.items():
                if not files:
                    continue

                files.sort(key=get_sort_index)

                images = []
                valid_files = []
                for img_name in files:
                    try:
                        img_path = os.path.join(date_path, img_name)
                        img = Image.open(img_path)
                        img.load()
                        images.append(img)
                        valid_files.append(img_path)
                    except:
                        pass
                if not images:
                    continue

                cols = 3
                rows = math.ceil(len(images) / cols)
                max_width = max(img.size[0] for img in images)
                max_height = max(img.size[1] for img in images)

                grid_width = cols * max_width
                grid_height = rows * max_height
                new_im = Image.new('RGB', (grid_width, grid_height), color='white')

                for i, img in enumerate(images):
                    x_offset = (i % cols) * max_width
                    y_offset = (i // cols) * max_height
                    new_im.paste(img, (x_offset, y_offset))
                    img.close()

                save_filename = f"HY202103_{wafer}_({c_val},{r_val})_LION1_DCM_{band}.png"
                new_im.save(os.path.join(date_path, save_filename))
                combine_count += 1

                if delete_originals:
                    for orig_path in valid_files:
                        try:
                            os.remove(orig_path)
                            deleted_count += 1
                        except Exception as e:
                            print(f"  [경고] 원본 파일 삭제 실패 ({os.path.basename(orig_path)}): {e}")

    print(f"  ✅ 총 {combine_count}개의 다이(Die) 요약 이미지 병합 완료!")
    if delete_originals:
        print(f"  🧹 병합에 사용된 원본 이미지 총 {deleted_count}개 삭제 완료.\n")


def merge_wafer_maps(base_dir, delete_originals=True):
    """🌟 WaferMap 폴더 내의 웨이퍼 맵 3종(ER, IL, VpiL)을 1개의 이미지로 가로 병합합니다."""
    wafermap_dir = os.path.join(base_dir, "WaferMap")
    if not os.path.exists(wafermap_dir):
        print(f"  [안내] WaferMap 폴더가 없어 웨이퍼 맵 병합을 건너뜁니다.")
        return

    print("▶ 2. 웨이퍼별 통합 맵(ER, IL, VpiL) 병합 및 원본 파일 관리를 시작합니다...")
    map_combine_count = 0
    deleted_count = 0

    for wafer in os.listdir(wafermap_dir):
        w_path = os.path.join(wafermap_dir, wafer)
        if not os.path.isdir(w_path):
            continue

        for date_folder in os.listdir(w_path):
            d_path = os.path.join(w_path, date_folder)
            if not os.path.isdir(d_path):
                continue

            band_images = {}
            for f in os.listdir(d_path):
                if f.startswith('Summary_WaferMap'):
                    try:
                        os.remove(os.path.join(d_path, f))
                    except:
                        pass
                    continue

                if f.startswith('Map_') and f.endswith('.png'):
                    # 파일명 예: Map_D07_LMZO_20190715_IL.png
                    parts = f.replace(f"Map_{wafer}_", "").split("_")
                    band = parts[0]
                    if band not in band_images:
                        band_images[band] = []
                    band_images[band].append(f)

            for band, files in band_images.items():
                if len(files) < 2:
                    continue

                files.sort(key=get_map_sort_index)

                images = []
                valid_files = []
                for f in files:
                    try:
                        img_path = os.path.join(d_path, f)
                        img = Image.open(img_path)
                        img.load()
                        images.append(img)
                        valid_files.append(img_path)
                    except:
                        pass

                if not images:
                    continue

                cols = len(images)
                max_width = max(img.size[0] for img in images)
                max_height = max(img.size[1] for img in images)

                new_im = Image.new('RGB', (max_width * cols, max_height), color='white')
                for i, img in enumerate(images):
                    new_im.paste(img, (i * max_width, 0))
                    img.close()

                save_filename = f"Summary_WaferMap_{wafer}_{band}_{date_folder}.png"
                new_im.save(os.path.join(d_path, save_filename))
                map_combine_count += 1

                if delete_originals:
                    for orig_path in valid_files:
                        try:
                            os.remove(orig_path)
                            deleted_count += 1
                        except Exception as e:
                            print(f"  [경고] 웨이퍼 맵 원본 삭제 실패 ({os.path.basename(orig_path)}): {e}")

    print(f"  ✅ 총 {map_combine_count}장의 통합 웨이퍼 맵 생성 완료!")
    if delete_originals:
        print(f"  🧹 병합에 사용된 웨이퍼 맵 원본 이미지 총 {deleted_count}개 삭제 완료.\n")


def merge_box_plots(base_dir, delete_originals=True):
    """🌟 BoxPlot 폴더 내의 박스 플롯 3종(ER, IL, VpiL)을 1개의 이미지로 가로 병합합니다."""
    boxplot_dir = os.path.join(base_dir, "BoxPlot")
    if not os.path.exists(boxplot_dir):
        print(f"  [안내] BoxPlot 폴더가 없어 박스 플롯 병합을 건너뜁니다.")
        return

    print("▶ 3. 통합 박스 플롯(ER, IL, VpiL) 병합 및 원본 파일 관리를 시작합니다...")
    box_combine_count = 0
    deleted_count = 0

    for wafer in os.listdir(boxplot_dir):
        w_path = os.path.join(boxplot_dir, wafer)
        if not os.path.isdir(w_path):
            continue

        for date_folder in os.listdir(w_path):
            d_path = os.path.join(w_path, date_folder)
            if not os.path.isdir(d_path):
                continue

            band_images = {}
            for f in os.listdir(d_path):
                if f.startswith('Summary_BoxPlot'):
                    try:
                        os.remove(os.path.join(d_path, f))
                    except:
                        pass
                    continue

                if f.startswith('Box_') and f.endswith('.png'):
                    # 파일명 예: Box_D07_LMZO_20190715_IL.png
                    parts = f.replace(f"Box_{wafer}_", "").split("_")
                    band = parts[0]
                    if band not in band_images:
                        band_images[band] = []
                    band_images[band].append(f)

            for band, files in band_images.items():
                if len(files) < 2:
                    continue

                files.sort(key=get_map_sort_index)

                images = []
                valid_files = []
                for f in files:
                    try:
                        img_path = os.path.join(d_path, f)
                        img = Image.open(img_path)
                        img.load()
                        images.append(img)
                        valid_files.append(img_path)
                    except:
                        pass

                if not images:
                    continue

                cols = len(images)
                max_width = max(img.size[0] for img in images)
                max_height = max(img.size[1] for img in images)

                new_im = Image.new('RGB', (max_width * cols, max_height), color='white')
                for i, img in enumerate(images):
                    new_im.paste(img, (i * max_width, 0))
                    img.close()

                save_filename = f"Summary_BoxPlot_{wafer}_{band}_{date_folder}.png"
                new_im.save(os.path.join(d_path, save_filename))
                box_combine_count += 1

                if delete_originals:
                    for orig_path in valid_files:
                        try:
                            os.remove(orig_path)
                            deleted_count += 1
                        except Exception as e:
                            print(f"  [경고] 박스 플롯 원본 삭제 실패 ({os.path.basename(orig_path)}): {e}")

    print(f"  ✅ 총 {box_combine_count}장의 통합 박스 플롯 생성 완료!")
    if delete_originals:
        print(f"  🧹 병합에 사용된 박스 플롯 원본 이미지 총 {deleted_count}개 삭제 완료.\n")


def main():
    base_dir = "../res/png"
    base_dir = os.path.abspath(base_dir)

    if not os.path.exists(base_dir):
        print(f"❌ [오류] {base_dir} 경로를 찾을 수 없습니다.")
        return

    # 🌟 원본 파일을 실제로 삭제하려면 True, 원본을 유지하고 싶다면 False로 설정하세요.
    DELETE_ORIGINAL_FILES = True

    # 1. Die 이미지 병합 실행
    merge_die_images(base_dir, delete_originals=DELETE_ORIGINAL_FILES)

    # 2. Wafer Map 이미지 병합 실행 (새 경로 적용)
    merge_wafer_maps(base_dir, delete_originals=DELETE_ORIGINAL_FILES)

    # 3. Box Plot 이미지 병합 실행 (새로 추가)
    merge_box_plots(base_dir, delete_originals=DELETE_ORIGINAL_FILES)

    print("\n🎉 모든 이미지 병합 및 원본 파일 정리 작업이 성공적으로 마무리되었습니다!")


if __name__ == "__main__":
    main()