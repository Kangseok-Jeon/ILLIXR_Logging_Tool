import os
import re
import pandas as pd
import matplotlib.pyplot as plt

# 🔹 로그 파싱용 정규식 패턴
patterns = {
    'tracking': re.compile(r"\[TIME\]:\s*([\d.]+)\s*ms\s*for\s*tracking"),
    'propagation': re.compile(r"\[TIME\]:\s*([\d.]+)\s*ms\s*for\s*propagation"),
    'msckf': re.compile(r"\[TIME\]:\s*([\d.]+)\s*ms\s*for\s*MSCKF update"),
    'slam_update': re.compile(r"\[TIME\]:\s*([\d.]+)\s*ms\s*for\s*SLAM update"),
    'slam_delay': re.compile(r"\[TIME\]:\s*([\d.]+)\s*ms\s*for\s*SLAM delayed init"),
    'marg': re.compile(r"\[TIME\]:\s*([\d.]+)\s*ms\s*for\s*marginalization"),
    'total': re.compile(r"\[TIME\]:\s*([\d.]+)\s*ms\s*for\s*total")
}

# 🔹 로그 한 개를 파싱하는 함수
def parse_log(filepath):
    data = {k: [] for k in patterns.keys()}
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            for key, pattern in patterns.items():
                match = pattern.search(line)
                if match:
                    data[key].append(float(match.group(1)))
    return pd.DataFrame(data)

# 🔹 통계표 시각화 및 저장 함수 (boxplot 제거 버전)
def save_summary_table(df, title, save_dir):
    stats = df.describe(percentiles=[0.25, 0.5, 0.75]).T[['mean', '25%', '50%', '75%']]

    # ✅ 통계표 시각화 및 저장
    fig, ax = plt.subplots(figsize=(8, 3))
    ax.axis('tight')
    ax.axis('off')
    table = ax.table(
        cellText=stats.round(3).values,
        colLabels=stats.columns,
        rowLabels=stats.index,
        loc='center'
    )
    table.scale(1, 1.2)
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    plt.title(f"{title} — Summary Statistics (ms)")
    plt.tight_layout()

    table_path = os.path.join(save_dir, f"{title}_table.png")
    plt.savefig(table_path, dpi=300)
    plt.close()
    print(f"📄 Saved table → {table_path}")

    # ✅ CSV 저장
    csv_path = os.path.join(save_dir, f"{title}_stats.csv")
    stats.to_csv(csv_path, float_format="%.3f")
    print(f"🧾 Saved stats CSV → {csv_path}\n")

# 🔹 data 폴더 내 모든 로그 처리
data_folder = r"C:\Users\study\Downloads\data"
save_folder = os.path.join(data_folder, "results")
os.makedirs(save_folder, exist_ok=True)

log_files = [f for f in os.listdir(data_folder) if f.endswith(".log")]

if not log_files:
    print("⚠️ 로그 파일을 찾을 수 없습니다.")
else:
    for log_name in log_files:
        filepath = os.path.join(data_folder, log_name)
        print(f"📘 Processing {log_name} ...")
        df = parse_log(filepath)
        if df.empty:
            print(f"  → {log_name} 에서 유효한 데이터가 없습니다.\n")
            continue
        save_summary_table(df, os.path.splitext(log_name)[0], save_folder)
