"""
openvins_klt_parser.py
----------------------
[TIME-KLT] 로그를 자동으로 CSV와 그래프로 변환하는 스크립트
"""

import os
import re
import pandas as pd
import matplotlib.pyplot as plt

# === 1. 경로 설정 ===
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
RESULTS_DIR = os.path.join(DATA_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# === 2. 로그 파일 목록 ===
log_files = [f for f in os.listdir(DATA_DIR) if f.endswith(".log")]

# === 3. 정규식 패턴 ===
pattern = re.compile(r"\[TIME-KLT\]:\s+([\d.]+)\s+ms\s+for\s+(.+)")

# === 4. 각 로그 파일 처리 ===
for log_file in log_files:
    log_path = os.path.join(DATA_DIR, log_file)
    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        text = f.read()

    # ANSI 색상 코드 제거
    text = re.sub(r"\x1B\[[0-9;]*[A-Za-z]", "", text)

    # 데이터 추출
    matches = pattern.findall(text)
    if not matches:
        print(f"⚠️ No [TIME-KLT] entries found in {log_file}")
        continue

    data = {}
    for time_str, step in matches:
        step = step.strip().split("(")[0].strip()  # "(xx features)" 등 제거
        data.setdefault(step, []).append(float(time_str))

    # === 5. 통계 계산 ===
    df = pd.DataFrame({step: vals for step, vals in data.items()})
    stats = df.describe(percentiles=[0.25, 0.5, 0.75]).T[["mean", "25%", "50%", "75%"]]

    # === 6. CSV 저장 ===
    csv_name = log_file.replace(".log", "_klt_stats.csv")
    csv_path = os.path.join(RESULTS_DIR, csv_name)
    stats.to_csv(csv_path, float_format="%.4f")
    print(f"✅ Saved: {csv_path}")

    # === 7. 표 그래프 저장 ===
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.axis("off")
    table = ax.table(
        cellText=stats.values,
        rowLabels=stats.index,
        colLabels=stats.columns,
        loc="center"
    )
    table.scale(1, 1.5)
    plt.title(f"{log_file.replace('.log','')} — KLT Timing Summary (ms)")
    png_path = os.path.join(RESULTS_DIR, log_file.replace(".log", "_klt_table.png"))
    plt.savefig(png_path, bbox_inches="tight", dpi=200)
    plt.close()
    print(f"📊 Table saved: {png_path}")

print("\n✅ All KLT logs processed successfully.")
