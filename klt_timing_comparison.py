"""
klt_timing_comparison.py
------------------------
각 앱별 KLT 실행 시간 통계(mean, 25%, 50%, 75%) 비교 그래프 생성
"""

import os
import pandas as pd
import matplotlib.pyplot as plt

# === 1. 경로 설정 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_DIR = os.path.join(BASE_DIR, "data", "results")
PLOT_DIR = os.path.join(RESULTS_DIR, "plots")
os.makedirs(PLOT_DIR, exist_ok=True)

# === 2. CSV 파일 목록 ===
files = {
    "materials": os.path.join(RESULTS_DIR, "materials_klt_stats.csv"),
    "openxr": os.path.join(RESULTS_DIR, "openxr_klt_stats.csv"),
    "spaceship": os.path.join(RESULTS_DIR, "spaceship_klt_stats.csv")
}

# === 3. CSV 로드 ===
dfs = {}
for name, path in files.items():
    if os.path.exists(path):
        df = pd.read_csv(path, index_col=0)
        dfs[name] = df
    else:
        print(f"⚠️ 파일이 없습니다: {path}")

# === 4. 시각화할 통계 항목 ===
metrics = ["mean", "25%", "50%", "75%"]

# === 5. 그래프 생성 ===
for metric in metrics:
    plt.figure(figsize=(10, 6))
    
    # 각 로그의 metric 열만 모아 데이터프레임 생성
    metric_df = pd.DataFrame({name: df[metric] for name, df in dfs.items()})
    
    metric_df.plot(kind="bar", figsize=(10, 6))
    plt.title(f"KLT {metric} Execution Time Comparison (ms)")
    plt.ylabel("Time (ms)")
    plt.xlabel("KLT Processing Step")
    plt.xticks(rotation=45)
    plt.legend(title="Scene")
    plt.tight_layout()
    
    # === 6. 그래프 저장 ===
    save_path = os.path.join(PLOT_DIR, f"klt_comparison_{metric}.png")
    plt.savefig(save_path, dpi=200)
    plt.close()
    print(f"📊 그래프 저장 완료: {save_path}")

print("\n✅ 모든 KLT 비교 그래프 생성 완료!")
