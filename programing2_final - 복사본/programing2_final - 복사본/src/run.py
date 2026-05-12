import os
import subprocess


def run_scripts():
    # 스크립트들이 있는 폴더 이름
    src_folder = "src"
    # 제외할 파일 이름
    exclude_file = "data_parser.py"

    # src 폴더 내의 모든 파일 확인
    if not os.path.exists(src_folder):
        print(f"'{src_folder}' 폴더를 찾을 수 없습니다.")
        return

    # .py 파일만 찾고, exclude_file은 제외
    scripts_to_run = [
        f for f in os.listdir(src_folder)
        if f.endswith('.py') and f != exclude_file
    ]

    # 알파벳 순으로 정렬 (필요에 따라 주석 처리/수정 가능)
    scripts_to_run.sort()

    if not scripts_to_run:
        print("실행할 파이썬 파일이 없습니다.")
        return

    print(f"총 {len(scripts_to_run)}개의 스크립트를 실행합니다...\n" + "-" * 40)

    # 각 스크립트 순차적 실행
    for script in scripts_to_run:
        script_path = os.path.join(src_folder, script)
        print(f"▶ 실행 중: {script} ...")

        # subprocess를 이용해 파이썬 파일 실행
        # Windows의 경우 'python', Mac/Linux의 경우 'python3'를 주로 사용합니다.
        result = subprocess.run(['python', script_path], capture_output=True, text=True)

        # 실행 결과 확인
        if result.returncode == 0:
            print(f"✅ 완료: {script}")
            # 만약 각 스크립트의 출력(print) 내용도 보고 싶다면 아래 주석을 해제하세요.
            # print(result.stdout)
        else:
            print(f"❌ 오류 발생 ({script}):")
            print(result.stderr)
            print("다음 스크립트 실행을 계속합니다...\n")


if __name__ == "__main__":
    run_scripts()