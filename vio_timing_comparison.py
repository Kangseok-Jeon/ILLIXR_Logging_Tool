import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import date

# === 1. 경로 설정 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # 현재 스크립트 위치
DATA_DIR = os.path.join(BASE_DIR, "data", "results")   # data/results 폴더 경로

# === 2. 파일 경로 지정 ===
files = {
    "spaceship": os.path.join(DATA_DIR, "spaceship_stats.csv"),
    "materials": os.path.join(DATA_DIR, "materials_stats.csv"),
    "openxr": os.path.join(DATA_DIR, "openxr_stats.csv")
}

# === 3. CSV 불러오기 ===
dfs = {}
for name, path in files.items():
    if os.path.exists(path):
        df = pd.read_csv(path)
        df.set_index(df.columns[0], inplace=True)
        dfs[name] = df
    else:
        print(f"⚠️ 파일을 찾을 수 없습니다: {path}")

# === 4. 통계 항목 ===
metrics = ["mean", "25%", "50%", "75%"]

# === 5. 그래프 저장 폴더 ===
SAVE_DIR = os.path.join(DATA_DIR, "plots")
os.makedirs(SAVE_DIR, exist_ok=True)

# === 6. 그래프 생성 ===
for metric in metrics:
    plt.figure(figsize=(10, 6))
    metric_values = pd.DataFrame({name: df[metric] for name, df in dfs.items()})
    metric_values.plot(kind="bar", figsize=(10, 6))
    plt.title(f"Comparison of {metric} Execution Times (ms)")
    plt.ylabel("Time (ms)")
    plt.xlabel("Process Step")
    plt.xticks(rotation=45)
    plt.legend(title="Scene")
    plt.tight_layout()
    
    save_name = os.path.join(SAVE_DIR, f"vio_timing_comparison_{metric}.png")
    plt.savefig(save_name)
    plt.close()

print("✅ 그래프 저장 완료:", SAVE_DIR)
