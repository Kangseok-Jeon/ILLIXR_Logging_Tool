# -*- coding: utf-8 -*-
"""
여러 실험 폴더의 periodic_log.csv를 찾아
analyze/<폴더명>/ 에 plot들을 저장하는 버전
"""

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import shutil
from pathlib import Path

# ====== 사용자 설정 ======
# 1) 부모 폴더 아래의 하위 폴더에서 periodic_log.csv 자동 탐색 (예: /exp_runs/openxr_15W, /exp_runs/materials_15W 등)
DATA_ROOT = Path("/home/nokdujeon/kangseok/ILLIXR/build")  # 부모 폴더
SEARCH_DEPTH = 2  # 하위 몇 단계까지 탐색할지 (openxr_15W/periodic_log.csv, A/B/periodic_log.csv 같은 구조 대응)

# 2) 혹시 특정 폴더만 지정하고 싶다면 여기에 직접 리스트로 주면 됨 (None이면 자동 탐색 사용)
DATASETS = None
# DATASETS = [
#     Path("/home/.../openxr_15W"),
#     Path("/home/.../materials_15W"),
# ]

# 3) 출력 루트 (여기 아래에 <폴더명>/figure/ 로 저장됨)
ANALYZE_ROOT = Path("/home/nokdujeon/kangseok/ILLIXR/analyze")


# ===== 공통 유틸 =====
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    for enc in ("utf-8", "cp949", "euc-kr", "utf-8-sig"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    return pd.read_csv(path, encoding_errors="ignore")

def copy_csv_to_analyze(csv_path: Path, out_root: Path):
    """periodic_log.csv 파일을 analyze/<폴더명>/로 복사"""
    exp_name = csv_path.parent.name
    dest_dir = out_root / exp_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / "periodic_log.csv"

    try:
        shutil.copy2(csv_path, dest_path)
        print(f"[COPIED] {csv_path} → {dest_path}")
    except Exception as e:
        print(f"[WARN] CSV 복사 실패: {csv_path} → {e}")

def find_time_column(df: pd.DataFrame):
    cand = [c for c in df.columns if re.search(r"(time|date)", str(c), re.I)]
    for p in ("timestamp", "[Time]", "time", "datetime", "date"):
        for c in df.columns:
            if str(c).lower() == p.lower():
                return c
    return cand[0] if cand else None

def parse_time_column(df: pd.DataFrame, time_col: str):
    """성공 시: ('_time_parsed', True), 실패 시: ('_time_index', False)"""
    if time_col is None:
        df["_time_index"] = np.arange(len(df)) * 100
        return "_time_index", False

    ser = pd.to_numeric(df[time_col], errors="coerce")
    if ser.notna().sum() > 0:
        med = ser.dropna().median()
        if med > 1e12:
            dt = pd.to_datetime(ser, unit="ms", errors="coerce")
            df["_time_parsed"] = dt
            return "_time_parsed", True
        elif med > 1e9:
            dt = pd.to_datetime(ser, unit="s", errors="coerce")
            df["_time_parsed"] = dt
            return "_time_parsed", True
        else:
            df["_time_index"] = ser
            return "_time_index", False

    df["_time_index"] = np.arange(len(df))
    return "_time_index", False

def ensure_numeric(df: pd.DataFrame, cols):
    out = []
    for c in cols:
        if c not in df.columns:
            continue
        s = df[c]
        if s.dtype == object:
            s = s.astype(str).str.replace(r"[%,]", "", regex=True).str.strip()
        df[f"__num__{c}"] = pd.to_numeric(s, errors="coerce")
        out.append(f"__num__{c}")
    return out

def plot_series(x, y, title, ylabel, save_dir: Path):
    save_dir.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(11, 4.5))
    plt.plot(x, y)
    plt.title(title)
    plt.xlabel("Time (ms)")
    plt.ylabel(ylabel)

    ax = plt.gca()

    if np.issubdtype(np.array(x).dtype, np.datetime64) or hasattr(x, "dt"):
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S\n%Y-%m-%d"))
        plt.gcf().autofmt_xdate()
        plt.xlabel("Time")
    else:
        import matplotlib.ticker as ticker
        ax.xaxis.set_minor_locator(ticker.MultipleLocator(1000))
        ax.grid(which="minor", linestyle=":", alpha=0.4)

    plt.tight_layout()
    out_path = save_dir / f"{title.lower().replace(' ', '_')}.png"
    plt.savefig(out_path, dpi=150)
    print(f"[SAVED] {out_path}")
    plt.close()


# ===== 단일 CSV 처리 =====
def process_csv(csv_path: Path, out_root: Path):
    copy_csv_to_analyze(csv_path, out_root)
    df = load_csv(csv_path)

    # 시간축
    time_col_raw = find_time_column(df)
    time_col, is_dt = parse_time_column(df, time_col_raw)
    x = df[time_col]

    # 저장 디렉터리: analyze/<실험폴더명>/figure
    exp_name = csv_path.parent.name  # 예: openxr_15W
    save_dir = out_root / exp_name / "figure"

    # ---- CPU 평균 Util (CPU0_util~CPU5_util) ----
    cpu_cols = [c for c in df.columns if re.fullmatch(r"CPU[0-5]_util", str(c))]
    if not cpu_cols:
        cpu_cols = [c for c in df.columns if re.match(r"cpu[0-5]_util", str(c), re.I)]
    cpu_nums = ensure_numeric(df, cpu_cols)
    if cpu_nums:
        cpu_avg = df[cpu_nums].mean(axis=1)
        plot_series(x, cpu_avg.rolling(5, min_periods=1).mean(),
                    "CPU Utilization (Avg of 6 cores)", "Percent", save_dir)
    else:
        print(f"[INFO] ({exp_name}) CPU0_util~CPU5_util 컬럼을 찾지 못했습니다. (컬럼명을 확인하세요)")

    # ---- 각 코어별 Utilization ----
    core_cols = [c for c in df.columns if re.fullmatch(r"CPU\d+_util", str(c), re.I)]
    if not core_cols:
        core_cols = [c for c in df.columns if re.match(r"cpu\d+_util", str(c), re.I)]
    core_num_cols = ensure_numeric(df, core_cols)

    if core_num_cols:
        def core_key(num_col_name: str) -> int:
            m = re.search(r"CPU(\d+)_util", num_col_name, re.I)
            return int(m.group(1)) if m else 10**9

        core_num_cols = sorted(core_num_cols, key=core_key)
        label_map = {col: re.sub(r"^__num__", "", col) for col in core_num_cols}

        for ncol in core_num_cols:
            y_core = df[ncol].rolling(5, min_periods=1).mean()
            core_label = label_map[ncol]
            plot_series(x, y_core, f"CPU Utilization {core_label}", "Percent", save_dir)
    else:
        print(f"[INFO] ({exp_name}) CPU#_util 컬럼(코어별)을 찾지 못했습니다.")

    # ---- CPU Frequency (현재값 평균) ----
    # 예: CPU0_freq, CPU1_freq, ...  (CPU*_max_freq 는 제외)
    freq_cols = [c for c in df.columns if re.fullmatch(r"CPU\d+_freq", str(c))]
    if not freq_cols:
        # 혹시 소문자 등 변형 대응
        freq_cols = [c for c in df.columns if re.match(r"cpu\d+_freq$", str(c), re.I)]

    freq_num_cols = ensure_numeric(df, freq_cols)
    if freq_num_cols:
        # sysfs scaling_cur_freq 단위가 kHz이므로 MHz로 변환
        cpu_freq_avg_mhz = df[freq_num_cols].mean(axis=1) / 1000.0
        plot_series(
            x,
            cpu_freq_avg_mhz.rolling(5, min_periods=1).mean(),
            "CPU Frequency (Average of cores)",
            "MHz",
            save_dir
        )
    else:
        print(f"[INFO] ({exp_name}) CPU*_freq 컬럼을 찾지 못했습니다. (_max_freq 제외)")

    # ---- GPU Utilization ----
    gpu_util_cols = [c for c in df.columns if re.search(r"(^|_)gpu(_|).*util$", str(c), re.I)]
    gpu_load_cols = [c for c in df.columns if re.search(r"(^|_)gpu(_|).*load$", str(c), re.I)]

    y_gpu = None
    if gpu_util_cols:
        util_num = ensure_numeric(df, [gpu_util_cols[0]])[0]
        raw = df[util_num]
        y_gpu = np.where(raw > 255, raw / 10.0, raw * 100.0 / 255.0)
    elif gpu_load_cols:
        load_num = ensure_numeric(df, [gpu_load_cols[0]])[0]
        raw = df[load_num]
        y_gpu = np.where(raw > 255, raw / 10.0, raw * 100.0 / 255.0)

    if y_gpu is not None:
        plot_series(x, pd.Series(y_gpu).rolling(5, min_periods=1).mean(),
                    "GPU Utilization", "Percent", save_dir)
    else:
        print(f"[INFO] ({exp_name}) GPU util/load 컬럼을 찾지 못했습니다.")

    if "GPU_freq" in df.columns:
        num = ensure_numeric(df, ["GPU_freq"])[0]
        plot_series(x, df[num].rolling(5, min_periods=1).mean(),
                    "GPU Frequency", "Hz", save_dir)

    # ---- Temperature (모든 *_temp) ----
    temp_cols = [c for c in df.columns if re.search(r"(?:^|_)temp$", str(c), re.I)]
    temp_nums = ensure_numeric(df, temp_cols)
    if temp_nums:
        temp_avg = df[temp_nums].mean(axis=1) / 1000
        plot_series(x, temp_avg.rolling(5, min_periods=1).mean(),
                    "Temperature (Average of sensors)", "°C (approx.)", save_dir)
    else:
        print(f"[INFO] ({exp_name}) *_temp 형태의 온도 컬럼을 찾지 못했습니다.")

    # ---- Memory Utilization ----
    mem_pct_cols = [c for c in df.columns if re.search(r"(mem_used_pct|mem.*util|memory.*util)", str(c), re.I)]
    mem_pct_nums = ensure_numeric(df, mem_pct_cols)

    mem_util = None
    if mem_pct_nums:
        mem_util = df[mem_pct_nums].mean(axis=1)
    else:
        used_cols = [c for c in df.columns if re.search(r"(mem.*used|memory_used)", str(c), re.I)]
        total_cols = [c for c in df.columns if re.search(r"(mem.*total|memory_total)", str(c), re.I)]
        if used_cols and total_cols:
            used_num = ensure_numeric(df, [used_cols[0]])[0]
            total_num = ensure_numeric(df, [total_cols[0]])[0]
            with np.errstate(divide="ignore", invalid="ignore"):
                mem_util = (df[used_num] / df[total_num]) * 100.0

    if mem_util is not None:
        plot_series(x, mem_util.rolling(5, min_periods=1).mean(),
                    "Memory Utilization", "Percent", save_dir)
    else:
        print(f"[INFO] ({exp_name}) 메모리 퍼센트 또는 used/total 컬럼을 찾지 못했습니다.")

    print({
        "experiment": exp_name,
        "csv_path": str(csv_path),
        "time_column_found": time_col_raw,
        "time_column_used": time_col,
        "time_is_datetime": is_dt,
        "cpu_cols_used": [c.replace("__num__", "") for c in cpu_nums] if cpu_nums else [],
        "temp_cols_used": [c.replace("__num__", "") for c in temp_nums] if temp_nums else [],
        "mem_pct_cols_used": [c.replace("__num__", "") for c in mem_pct_nums] if mem_pct_nums else []
    })


# ===== 데이터셋 탐색 =====
def discover_datasets(data_root: Path, depth: int = 1):
    """
    data_root 아래에서 depth 단계까지 내려가며 periodic_log.csv 보유 폴더를 찾는다.
    """
    patterns = {
        1: "*",
        2: "*/*",
        3: "*/*/*",
    }
    pat = patterns.get(depth, "*")
    folders = []
    for csv_path in data_root.glob(f"{pat}/periodic_log.csv"):
        if csv_path.is_file():
            folders.append(csv_path.parent)
    return sorted(set(folders))


# ===== 메인 =====
def main():
    if DATASETS is not None:
        dataset_dirs = [Path(p) for p in DATASETS]
    else:
        dataset_dirs = discover_datasets(DATA_ROOT, depth=SEARCH_DEPTH)

    if not dataset_dirs:
        print(f"[WARN] {DATA_ROOT} 아래에서 periodic_log.csv를 찾지 못했습니다. (depth={SEARCH_DEPTH})")
        return

    print(f"[INFO] 발견된 실험 폴더 수: {len(dataset_dirs)}")
    for d in dataset_dirs:
        csv_path = d / "periodic_log.csv"
        try:
            process_csv(csv_path, ANALYZE_ROOT)
        except Exception as e:
            print(f"[ERROR] {d.name}: {e}")

if __name__ == "__main__":
    main()
