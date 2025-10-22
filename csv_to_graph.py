#!/usr/bin/env python3
import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = "/home/nokdujeon/kangseok/ILLIXR/analyze/data"
ANALYZE_DIR = "/home/nokdujeon/kangseok/ILLIXR/analyze"  # 앱별 하위 폴더 생성 기준

def read_duration_ms(path):
    s = pd.read_csv(path)["Duration (ns)"].astype("int64")
    return (s / 1_000_000.0).reset_index(drop=True)  # ns→ms

def normalize_x(n_points: int):
    if n_points == 1:
        return np.array([0.0])
    return np.linspace(0.0, 1.0, n_points)

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

def plot_for_app(app: str, files_for_app: list):
    # 앱별 출력 폴더(예: analyze/spaceship_nsys)
    out_dir = ensure_dir(os.path.join(ANALYZE_DIR, f"{app}_nsys"))

    # ===== 데이터 읽기: {stage: series(ms)} =====
    data = {}
    for p in files_for_app:
        name_no_ext = os.path.splitext(os.path.basename(p))[0]
        stage, _app = split_stage_app(name_no_ext)
        try:
            data[stage] = read_duration_ms(p)
        except Exception as e:
            print(f"[WARN] 읽기 실패: {p} ({e})")

    if not data:
        print(f"[INFO] {app}: 데이터 없음")
        return

    # ===== (1) 라인 그래프: 평균 실행시간 상위 2개 + 나머지 =====
    stats = sorted(((k, v.mean()) for k, v in data.items()),
                   key=lambda x: x[1], reverse=True)
    top_labels = [k for k, _ in stats[:2]]
    bottom_labels = [k for k, _ in stats[2:]]

    fig = plt.figure(figsize=(10, 5.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1])

    # Top
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_prop_cycle(color=plt.cm.tab10.colors)
    for lbl in top_labels:
        y = data[lbl].values
        x = normalize_x(len(y))
        ax1.plot(x, y, label=f"{lbl} (n={len(y)})")
    ax1.set_title(f"Execution Time per Plugin — {app}")
    ax1.set_ylabel("Time (ms)")
    ax1.set_xlim(0, 1)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(0, 200)

    # Bottom
    ax2 = fig.add_subplot(gs[1, 0])
    ax2.set_prop_cycle(color=plt.cm.Set2.colors)
    for lbl in bottom_labels:
        y = data[lbl].values
        x = normalize_x(len(y))
        ax2.plot(x, y, label=f"{lbl} (n={len(y)})")
    ax2.set_ylabel("Time (ms)")
    ax2.set_xlabel("Normalized progress (0→1)")
    ax2.set_xlim(0, 1)
    # 필요 시 확대 범위 조절
    # ax2.set_ylim(0, 10)
    if bottom_labels:
        ax2.legend(ncols=3, fontsize=9)
    ax2.grid(True, alpha=0.3)

    out_png = os.path.join(out_dir, "execution_time_per_plugin.png")
    plt.savefig(out_png, dpi=150)
    print(f"[완료] {app}: 라인 그래프 저장 → {out_png}")
    plt.close(fig)

    # ===== (2) 합계 기준 100% 스택 막대그래프 =====
    stage_sums_ms = {name: s.sum() for name, s in data.items()}
    total_ms = sum(stage_sums_ms.values())
    if total_ms <= 0:
        print(f"[경고] {app}: 합계 0 → 스택 그래프 생략")
        return

    stage_ratios = {k: v / total_ms * 100.0 for k, v in stage_sums_ms.items()}
    ordered = sorted(stage_ratios.items(), key=lambda x: x[1], reverse=True)

    palette = list(plt.cm.tab20.colors) + list(plt.cm.Set3.colors)
    fig2, ax = plt.subplots(figsize=(4.5, 4.2), constrained_layout=True)

    bottom = 0.0
    for i, (stage, pct) in enumerate(ordered):
        color = palette[i % len(palette)]
        ax.bar(0, pct, bottom=bottom, label=f"{stage}", color=color)
        bottom += pct

    ax.set_ylim(0, 100)
    ax.set_ylabel("%")
    ax.set_xticks([0])
    ax.set_xticklabels([f"{app}"])  # 앱 이름로 표기
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)

    out_png2 = os.path.join(out_dir, "execution_time_stack_percentage_sum.png")
    plt.savefig(out_png2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    print(f"[완료] {app}: 스택 막대그래프 저장 → {out_png2}")

    # 요약 CSV도 앱 폴더에 저장
    summary_csv = os.path.join(out_dir, "execution_time_summary_sum.csv")
    pd.DataFrame({
        "Stage": list(stage_sums_ms.keys()),
        "Total (ms)": list(stage_sums_ms.values()),
        "Ratio (%)": [stage_ratios[k] for k in stage_sums_ms.keys()]
    }).sort_values("Ratio (%)", ascending=False).to_csv(summary_csv, index=False)
    print(f"[완료] {app}: 요약 CSV 저장 → {summary_csv}")

def main():
    files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not files:
        print("CSV 없음"); return

    # 파일을 app별로 그룹핑 (마지막 '_' 뒤가 app)
    by_app = {}
    for p in files:
        name_no_ext = os.path.splitext(os.path.basename(p))[0]
        stage, app = split_stage_app(name_no_ext)
        by_app.setdefault(app, []).append(p)

    # 각 앱에 대해 처리
    for app, paths in sorted(by_app.items()):
        print(f"\n=== 처리: {app} (파일 {len(paths)}개) ===")
        plot_for_app(app, paths)

if __name__ == "__main__":
    main()
