#!/usr/bin/env python3
import os, glob
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

DATA_DIR = "/home/nokdujeon/kangseok/ILLIXR/analyze/data"
ANALYZE_DIR = "/home/nokdujeon/kangseok/ILLIXR/analyze"  # 앱별 하위 폴더 생성 기준

def read_ms(path: str) -> pd.Series:
    s = pd.read_csv(path)["Duration (ns)"].astype("int64")
    return (s / 1_000_000.0)  # ns → ms

def split_stage_app(filename_no_ext: str):
    """
    'OpenVINS_spaceship' -> ('OpenVINS', 'spaceship')
    'Timewarp_vk_openxr' -> ('Timewarp_vk', 'openxr')
    규칙: 마지막 '_' 뒤가 app 이름, 나머지는 stage 이름
    """
    if "_" not in filename_no_ext:
        return filename_no_ext, "unknown"
    head, app = filename_no_ext.rsplit("_", 1)
    return head, app

def ensure_dir(p):
    os.makedirs(p, exist_ok=True)
    return p

def plot_app(app: str, csv_paths: list):
    rows = []
    for p in csv_paths:
        name_no_ext = os.path.splitext(os.path.basename(p))[0]
        stage, _app = split_stage_app(name_no_ext)
        y = read_ms(p).dropna()
        if len(y) == 0:
            continue
        rows.append({
            "Stage": stage,
            "n": int(len(y)),
            "mean_ms": float(y.mean()),
            "min_ms": float(y.min()),
            "max_ms": float(y.max()),
        })

    if not rows:
        print(f"[INFO] {app}: 데이터가 비어 있습니다."); 
        return

    df = pd.DataFrame(rows).drop_duplicates(subset=["Stage"])
    df.sort_values("mean_ms", ascending=False, inplace=True, ignore_index=True)

    means = df["mean_ms"].values
    yerr = np.vstack([means - df["min_ms"].values, df["max_ms"].values - means])
    x = np.arange(len(df))
    labels = df["Stage"].values

    fig, ax = plt.subplots(figsize=(10, 5), constrained_layout=True)
    ax.bar(x, means, yerr=yerr, capsize=4, width=0.6)

    ax.set_ylabel("Time (ms)")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=20, ha="right")
    ax.set_title(f"Per-plugin mean with min/max — {app}")
    ax.grid(axis="y", alpha=0.3)

    # 값 표시
    for xi, mean, minv, maxv in zip(x, df["mean_ms"], df["min_ms"], df["max_ms"]):
        ax.text(xi, mean, f"{mean:.2f}", ha="center", va="bottom", fontsize=8, color="black")
        ax.text(xi, maxv, f"max {maxv:.2f}", ha="center", va="bottom", fontsize=7, color="red")
        ax.text(xi, minv, f"min {minv:.2f}", ha="center", va="top", fontsize=7, color="blue")

    out_dir = ensure_dir(os.path.join(ANALYZE_DIR, f"{app}_nsys"))
    out_png = os.path.join(out_dir, "bar_mean_min_max.png")
    plt.savefig(out_png, dpi=150)
    plt.close(fig)
    print(f"[완료] {app}: 저장 → {out_png}")

def main():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "*.csv")))
    if not files:
        print("CSV 없음"); 
        return

    # 앱별로 그룹핑
    by_app = {}
    for p in files:
        name_no_ext = os.path.splitext(os.path.basename(p))[0]
        _stage, app = split_stage_app(name_no_ext)
        by_app.setdefault(app, []).append(p)

    for app, paths in sorted(by_app.items()):
        print(f"\n=== 처리: {app} (파일 {len(paths)}개) ===")
        plot_app(app, paths)

if __name__ == "__main__":
    main()
