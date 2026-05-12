import subprocess
import os
import sys


def main():
    # 현재 run.py 파일이 있는 디렉토리 경로를 가져옵니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))

    # 실행할 스크립트들의 목록입니다.
    # 데이터 처리 -> 분석 -> 시각화 순서로 실행되도록 순서를 알맞게 조정해 주세요.
    # (아래는 임의로 논리적인 순서를 추정하여 작성한 예시입니다)
    scripts_to_run = [
        "data_parser.py",  # 1. 데이터 파싱
        "export_summary.py",
        "flatting.py",  # 2. 데이터 전처리 (플래트닝)
        "Fittinf_Savitzky.py",  # 3. 피팅
        "Phase shift - V.py",  # 4. 분석 1
        "VpiL.py",  # 5. 분석 2
        "VpiL_Analysis.py",  # 6. 분석 3
        "ER_Analysis.py",  # 7. 분석 4
        "IL_Analysis.py",  # 8. 분석 5
        "plot.py",  # 9. 시각화 1
        "zoom.py"  # 10. 시각화 2
    ]

    print("=== 통합 실행을 시작합니다 ===")

    for script in scripts_to_run:
        script_path = os.path.join(current_dir, script)

        # 파일이 실제로 존재하는지 확인
        if not os.path.exists(script_path):
            print(f"[경고] {script} 파일을 찾을 수 없습니다. 건너뜁니다.")
            continue

        print(f"\n▶ 실행 중: {script} ...")

        try:
            # sys.executable은 현재 파이썬 환경(python 또는 python3)을 자동으로 지정합니다.
            result = subprocess.run([sys.executable, script_path], check=True)
            print(f"▷ 완료: {script}")

        except subprocess.CalledProcessError as e:
            # 특정 스크립트에서 에러가 발생하면 실행을 중단합니다.
            print(f"\n[오류] {script} 실행 중 에러가 발생했습니다!")
            print(f"에러 코드: {e.returncode}")
            print("=== 전체 실행을 중단합니다 ===")
            break

    else:
        # for문이 break 없이 정상적으로 모두 끝났을 때 실행됩니다.
        print("\n=== 모든 스크립트 실행이 성공적으로 완료되었습니다! ===")


if __name__ == "__main__":
    main()