# 📂 Wafer Data Analysis & Integrated Reporting System

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-Data%20Analysis-150458?logo=pandas&logoColor=white)
![Matplotlib](https://img.shields.io/badge/Matplotlib-Visualization-black?logo=python)

> **XML 기반의 광학 소자(Wafer) 측정 데이터를 파싱하고, 정밀 분석(IL, ER, VpiL, Phase Shift)을 거쳐 시각화 및 통합 엑셀 대시보드를 생성하는 자동화 파이프라인입니다.**

본 프로젝트는 수많은 Mach-Zehnder Modulator(MZM) 소자의 테스트 데이터를 단 한 번의 실행으로 분석하고, 그 결과를 직관적인 엑셀 리포트와 요약 이미지로 출력하여 연구 및 데이터 검증 시간을 획기적으로 단축해 줍니다.

---

## 📁 디렉토리 구조 (Directory Structure)

정상적인 분석 실행을 위해 데이터와 스크립트가 아래의 구조를 유지해야 합니다. 

```text
📁 pycharm-project-root/
│
├── 📄 run.py                       # 🚀 통합 자동화 실행 파일 (One-click Execution)
│
├── 📁 dat/
│   └── 📄 data                     # 원본 웨이퍼 XML 압축 데이터 (예: HY202103.zip)
│
├── 📁 src/                         # 핵심 분석 모듈 폴더
│   ├── 📄 data_parser.py           
│   ├── 📄 plot.py                  
│   ├── 📄 flatting.py              
│   ├── 📄 zoom.py                  
│   ├── 📄 Fitting.py               
│   ├── 📄 Phase shift - V.py       
│   ├── 📄 VpiL.py                  
│   ├── 📄 ER_Analysis.py           
│   ├── 📄 IL_Analysis.py           
│   ├── 📄 VpiL_Analysis.py         
│   ├── 📄 combine_plot.py          
│   └── 📄 export_summary.py        
│
└── 📁 res/                         # 프로그램 실행 시 자동 생성되는 결과물 디렉토리
    ├── 📁 csv/                     # 요약 및 통합 데이터 CSV 모음
    │   ├── 📄 Analysis.csv             
    │   ├── 📄 Total_Process_result.csv 
    │   └── 📄 {Wafer_ID}_Process_result.csv 
    │
    ├── 📁 xlsx/                    # 하이퍼링크가 포함된 통합 엑셀 리포트 모음
    │   ├── 📄 Analysis.xlsm            
    │   ├── 📄 Total_Process_result.xlsx 
    │   └── 📄 {Wafer_ID}_Process_result.xlsx 
    │
    └── 📁 png/                     # 시각화 이미지 저장소
        ├── 📁 WaferMap/                # 웨이퍼별 ER, IL, VpiL 히트맵
        ├── 📁 BoxPlot/                 # 웨이퍼별 Center vs Edge Box Plot
        └── 📁 {Wafer_ID}/              # [개별 다이 데이터]
            └── 📁 {Date_YYYYMMDD}/     # 측정 날짜별 폴더 
                └── 📄 HY202103_{Wafer}_({C},{R})_LION1_DCM_{Band}.png  # ✨ 병합된 요약 이미지
```

---

## ⚙️ 데이터 분석 파이프라인 (Data Pipeline)

`run.py` 실행 시 내부적으로 9개의 핵심 모듈이 순차적으로 동작합니다. 복잡한 측정 신호가 어떻게 정제되고 분석되는지 아래 과정에서 확인할 수 있습니다.

### 1. 데이터 추출 및 초기 시각화 (`plot.py`)
측정 장비에서 얻은 원시 데이터(Raw Data)를 파싱하여 기본 스펙트럼 그래프를 그립니다.
> ![Raw Data Plot](https://via.placeholder.com/600x300?text=Insert+Raw+Data+Plot+Image+Here)

### 2. 신호 보정 (Flattening) (`flatting.py`)
MZM 소자와 기준(Reference) 소자 간에 발생하는 빛의 손실 편차를 보정합니다. 비스듬하게 측정된 신호의 베이스라인을 반듯하게 평탄화하여 정확한 분석의 토대를 마련합니다.
> ![Flattened Plot](https://via.placeholder.com/600x300?text=Insert+Flattened+Plot+Image+Here)

### 3. 분석 영역 집중 (Zoom) (`zoom.py`)
전체 파장 대역 중 밴드별로 가장 중요한 핵심 파장 영역만 돋보기처럼 확대하여 잘라냅니다.
* **LMZC 밴드:** **1550 nm** 영역 집중 분석
* **LMZO 밴드:** **1310 nm** 영역 집중 분석
> ![Zoomed Plot](https://via.placeholder.com/600x300?text=Insert+Zoomed+Plot+Image+Here)

### 4. 노이즈 제거 및 데이터 정제 (`Fitting.py`)
측정된 신호의 자글자글한 고주파 노이즈(Ripple)를 Savitzky-Golay 필터 등으로 걷어내고, 다항식 피팅(Polynomial Fitting)을 적용하여 신호를 부드럽고 정확한 곡선으로 다듬습니다.
> ![Fitting Plot](https://via.placeholder.com/600x300?text=Insert+Fitting+Plot+Image+Here)

### 5. 전압별 위상 변화 추적 (`Phase shift - V.py`)
피팅된 그래프에서 빛의 투과도가 가장 낮은 지점(Dip)을 찾고, 인가된 전압(Bias Voltage)이 변할 때마다 이 지점이 파장축을 따라 얼마나 이동(Shift)하는지 위상 변화량을 계산합니다.
> ![Phase Shift Plot](https://via.placeholder.com/600x300?text=Insert+Phase+Shift+Plot+Image+Here)

### 6. 최종 효율 지표(VpiL) 산출 (`VpiL.py`)
계산된 위상 변화량을 바탕으로 소자의 전광 변조 효율을 나타내는 핵심 지표인 **VpiL**을 추출하고 최종 트렌드 그래프를 생성합니다.
> ![VpiL Plot](https://via.placeholder.com/600x300?text=Insert+VpiL+Plot+Image+Here)

### 7. 대시보드 리포트 생성 (`combine_plot.py` & `export_summary.py`)
위 6가지 과정에서 생성된 모든 그래프를 단 한 장의 3x2 요약 이미지로 병합합니다. 또한, 측정된 모든 수치 데이터(IL, ER, VpiL)를 엑셀 파일로 정리하며, **클릭 한 번에 해당 소자의 요약 이미지를 띄울 수 있도록 엑셀 내부에 하이퍼링크를 자동 매핑**합니다.
> ![Combined Dashboard](https://via.placeholder.com/800x450?text=Insert+Combined+Dashboard+Image+Here)