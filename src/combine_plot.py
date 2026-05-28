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
    웨이퍼 맵 이미지의 정렬 순서를 결정합니다.
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


def merge_die_images(base_dir):
    """기존: 각 Die 폴더 내의 분석 이미지를 격자 형태로 병합합니다."""
    print("▶ 1. 개별 좌표(Die) 폴더 내 분석 이미지 병합을 시작합니다...")
    combine_count = 0

    for wafer in os.listdir(base_dir):
        wafer_path = os.path.join(base_dir, wafer)
        if not os.path.isdir(wafer_path) or wafer == "Analysis":
            continue

        for date_folder in os.listdir(wafer_path):
            date_path = os.path.join(wafer_path, date_folder)
            if not os.path.isdir(date_path):
                continue

            for coord_folder in os.listdir(date_path):
                coord_path = os.path.join(date_path, coord_folder)
                if not os.path.isdir(coord_path):
                    continue

                # 1) 기존 Summary 삭제
                for f in os.listdir(coord_path):
                    if f.startswith('Summary_') and f.endswith('.png'):
                        try:
                            os.remove(os.path.join(coord_path, f))
                        except:
                            pass

                # 2) 이미지 목록 추출 및 정렬
                image_files = [f for f in os.listdir(coord_path) if f.endswith('.png')]
                if not image_files:
                    continue
                image_files.sort(key=get_sort_index)

                # 3) 이미지 열기
                images = []
                for img_name in image_files:
                    try:
                        images.append(Image.open(os.path.join(coord_path, img_name)))
                    except:
                        pass
                if not images:
                    continue

                # 4) 병합 (2열 격자)
                cols = 2
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

                # 5) 저장
                save_filename = f"Summary_{wafer}_{coord_folder}.png"
                new_im.save(os.path.join(coord_path, save_filename))
                combine_count += 1

    print(f"  ✅ 총 {combine_count}개의 다이(Die) 요약 이미지 병합 완료!\n")


def merge_wafer_maps(base_dir):
    """신규: Analysis 폴더 내의 웨이퍼 맵 3종을 1개의 이미지로 가로 병합합니다."""
    analysis_dir = os.path.join(base_dir, "Analysis")
    if not os.path.exists(analysis_dir):
        print(f"  [안내] Analysis 폴더가 없어 웨이퍼 맵 병합을 건너뜁니다.")
        return

    print("▶ 2. 웨이퍼별 통합 맵(IL, ER, VpiL) 병합을 시작합니다...")
    map_combine_count = 0

    for wafer in os.listdir(analysis_dir):
        w_path = os.path.join(analysis_dir, wafer)
        if not os.path.isdir(w_path) or wafer == "Overall_BoxPlots":
            continue

        for date_folder in os.listdir(w_path):
            d_path = os.path.join(w_path, date_folder)
            if not os.path.isdir(d_path):
                continue

            # 대역(Band)별로 맵 파일 분류 (예: LMZC, LMZO)
            band_images = {}
            for f in os.listdir(d_path):
                # 기존에 만들어둔 요약본은 건너뜀
                if f.startswith('Summary_WaferMap'):
                    try:
                        os.remove(os.path.join(d_path, f))
                    except:
                        pass
                    continue

                # 웨이퍼 맵 이미지(Map_)인 경우 추출
                if f.startswith('Map_') and f.endswith('.png'):
                    # 파일명 구조: Map_{wafer}_{band}_{date}_{type}.png
                    # Band 이름을 파싱하여 그룹화
                    parts = f.replace(f"Map_{wafer}_", "").split("_")
                    band = parts[0]
                    if band not in band_images:
                        band_images[band] = []
                    band_images[band].append(f)

            # Band별로 가로 병합
            for band, files in band_images.items():
                if len(files) < 2:  # 합칠 맵이 2장 미만이면 패스
                    continue

                # 🌟 수정된 정렬 방식 (ER -> IL -> VpiL)이 적용되는 곳
                files.sort(key=get_map_sort_index)

                images = []
                for f in files:
                    try:
                        images.append(Image.open(os.path.join(d_path, f)))
                    except:
                        pass

                if not images:
                    continue

                # 가로로 길게 1행 다열 배치
                cols = len(images)
                max_width = max(img.size[0] for img in images)
                max_height = max(img.size[1] for img in images)

                # 이미지들을 옆으로 나란히 붙임
                new_im = Image.new('RGB', (max_width * cols, max_height), color='white')
                for i, img in enumerate(images):
                    new_im.paste(img, (i * max_width, 0))

                # 저장 (Analysis/웨이퍼/날짜/ 폴더 안에 저장됨)
                save_filename = f"Summary_WaferMap_{wafer}_{band}_{date_folder}.png"
                new_im.save(os.path.join(d_path, save_filename))
                map_combine_count += 1

    print(f"  ✅ 총 {map_combine_count}장의 통합 웨이퍼 맵(Dashboard) 생성 완료!")


def main():
    base_dir = "../res/png"
    base_dir = os.path.abspath(base_dir)

    if not os.path.exists(base_dir):
        print(f"❌ [오류] {base_dir} 경로를 찾을 수 없습니다.")
        return

    # 1. Die 이미지 병합 실행
    merge_die_images(base_dir)

    # 2. Wafer Map 이미지 병합 실행
    merge_wafer_maps(base_dir)

    print("\n🎉 모든 이미지 병합 작업이 성공적으로 마무리되었습니다!")


if __name__ == "__main__":
    main()