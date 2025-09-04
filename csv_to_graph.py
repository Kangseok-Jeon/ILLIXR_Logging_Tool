#!/usr/bin/env python3
import os, glob
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = "/home/nokdujeon/kangseok/ILLIXR/analyze/data"

def read_duration_ms(path):
    s = pd.read_csv(path)["Duration (ns)"].astype("int64")
    return (s / 1_000_000.0).reset_index(drop=True)  # ns→ms

def normalize_x(n_points: int):
    # 0~1 사이에 n_points개 점(양 끝 포함) 배치
    if n_points == 1:
        return np.array([0.0])
    return np.linspace(0.0, 1.0, n_points)

def main():
    files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    if not files:
        print("CSV 없음"); return

    # ====== (1) 라인 그래프: 실행시간 상위 2개는 위, 나머지는 아래 ======
    # 읽기
    data = {os.path.splitext(os.path.basename(p))[0]: read_duration_ms(p) for p in files}

    # 평균 실행시간 기준 상위 2개
    stats = sorted(((k, v.mean()) for k, v in data.items()), key=lambda x: x[1], reverse=True)
    top_labels = [k for k, _ in stats[:2]]
    bottom_labels = [k for k, _ in stats[2:]]

    # 플롯
    fig = plt.figure(figsize=(10, 5.2), constrained_layout=True)
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1])

    # Top
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_prop_cycle(color=plt.cm.tab10.colors)
    for lbl in top_labels:
        y = data[lbl].values
        x = normalize_x(len(y))          # 길이에 맞춘 0~1 정규화 x축
        ax1.plot(x, y, label=f"{lbl} (n={len(y)})")
    ax1.set_ylabel("Time (ms)")
    ax1.set_xlim(0, 1)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

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
    ax2.set_ylim(0, 10)
    # 필요 시 확대
    # ax2.set_ylim(0, 10)
    ax2.legend(ncols=3, fontsize=9)
    ax2.grid(True, alpha=0.3)

    out_png = os.path.join(DATA_DIR, "execution_time_per_plugin.png")
    plt.savefig(out_png, dpi=150)
    print(f"[완료] 라인 그래프 저장: {out_png}")
    plt.show()

    # ====== (2) 합계 기준 100% 스택 막대그래프 ======
    # 각 시리즈 합계(ms)
    stage_sums_ms = {name: s.sum() for name, s in data.items()}
    total_ms = sum(stage_sums_ms.values())

    # 비율(%) 계산
    if total_ms <= 0:
        print("[경고] 합계가 0입니다. 스택 그래프를 건너뜁니다.")
        return

    stage_ratios = {k: v / total_ms * 100.0 for k, v in stage_sums_ms.items()}

    # 보기 좋게 큰 순서로 정렬
    ordered = sorted(stage_ratios.items(), key=lambda x: x[1], reverse=True)

    # 색상 팔레트
    palette = list(plt.cm.tab20.colors) + list(plt.cm.Set3.colors)

    fig2, ax = plt.subplots(figsize=(4, 4), constrained_layout=True)

    bottom = 0.0
    for i, (stage, pct) in enumerate(ordered):
        color = palette[i % len(palette)]
        ax.bar(0, pct, bottom=bottom, label=f"{stage}", color=color)
        bottom += pct

    ax.set_ylim(0, 100)
    ax.set_ylabel("%")
    ax.set_xticks([0])
    ax.set_xticklabels(["Total"])  # 합계 기준 표시
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=9)

    out_png2 = os.path.join(DATA_DIR, "execution_time_stack_percentage_sum.png")
    plt.savefig(out_png2, dpi=150, bbox_inches="tight")
    plt.show()
    print(f"[완료] 스택 막대그래프 저장(합계 기준): {out_png2}")

    # 요약 CSV도 저장
    summary_csv = os.path.join(DATA_DIR, "execution_time_summary_sum.csv")
    pd.DataFrame({
        "Stage": list(stage_sums_ms.keys()),
        "Total (ms)": list(stage_sums_ms.values()),
        "Ratio (%)": [stage_ratios[k] for k in stage_sums_ms.keys()]
    }).sort_values("Ratio (%)", ascending=False).to_csv(summary_csv, index=False)
    print(f"[완료] 요약 CSV 저장(합계 기준): {summary_csv}")


if __name__ == "__main__":
    main()
