# -*- coding: utf-8 -*-
"""
periodic_log.csv → CPU 평균 Util, Temperature, Memory Util 그래프화
- CPU: CPU0_util~CPU5_util 평균
- Temp: *_temp 컬럼 전부
- Mem: Mem_used_pct 또는 (Mem_used_kB / Mem_total_kB * 100)
- 시간축 자동 처리: datetime 파싱 성공 시 시간, 실패 시 인덱스
"""

import re
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from pathlib import Path

CSV_PATH = Path("/home/nokdujeon/kangseok/ILLIXR/build/logger/periodic_log.csv")

# ===== 공통 유틸 =====
def load_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")
    for enc in ("utf-8", "cp949", "euc-kr", "utf-8-sig"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    # 그래도 실패하면 최대한 읽기
    return pd.read_csv(path, encoding_errors="ignore")

def find_time_column(df: pd.DataFrame):
    # time/date 관련 컬럼 후보
    cand = [c for c in df.columns if re.search(r"(time|date)", str(c), re.I)]
    # 자주 쓰는 이름 우선
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

    # 1) 숫자형이면 epoch(s/ms) 가정
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
            # 단순 증가 인덱스로 사용
            df["_time_index"] = ser
            return "_time_index", False

    # 2) 완전 실패 → 인덱스
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

def plot_series(x, y, title, ylabel):
    plt.figure(figsize=(11, 4.5))
    plt.plot(x, y)
    plt.title(title)
    plt.xlabel("Time (ms)")
    plt.ylabel(ylabel)
    # datetime x축이면 자동 포맷
    if np.issubdtype(np.array(x).dtype, np.datetime64) or hasattr(x, "dt"):
        ax = plt.gca()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S\n%Y-%m-%d"))
        plt.gcf().autofmt_xdate()
    plt.tight_layout()
    plt.show()
    # 저장을 원하면 아래 주석 해제
    # out_path = f"/mnt/data/{title.lower().replace(' ', '_')}.png"
    # plt.savefig(out_path, dpi=150); plt.close()

# ===== 메인 처리 =====
def main():
    df = load_csv(CSV_PATH)

    # 시간축
    time_col_raw = find_time_column(df)
    time_col, is_dt = parse_time_column(df, time_col_raw)
    x = df[time_col]

    # ---- CPU 평균 Util (CPU0_util~CPU5_util) ----
    cpu_cols = [c for c in df.columns if re.fullmatch(r"CPU[0-5]_util", str(c))]
    if not cpu_cols:
        # 혹시 이름이 약간 다른 경우(소문자 등)까지 커버
        cpu_cols = [c for c in df.columns if re.match(r"cpu[0-5]_util", str(c), re.I)]
    cpu_nums = ensure_numeric(df, cpu_cols)
    if cpu_nums:
        cpu_avg = df[cpu_nums].mean(axis=1)  # 6개 평균
        plot_series(x, cpu_avg.rolling(5, min_periods=1).mean(), "CPU Utilization (Avg of 6 cores)", "Percent")
    else:
        print("[INFO] CPU0_util~CPU5_util 컬럼을 찾지 못했습니다. (컬럼명을 확인하세요)")

    # ---- Temperature (모든 *_temp) ----
    temp_cols = [c for c in df.columns if re.search(r"(?:^|_)temp$", str(c), re.I)]
    temp_nums = ensure_numeric(df, temp_cols)
    if temp_nums:
        # 센서가 여러 개면 평균으로 1개 그래프
        temp_avg = df[temp_nums].mean(axis=1)
        plot_series(x, temp_avg.rolling(5, min_periods=1).mean(), "Temperature (Average of sensors)", "°C (approx.)")
    else:
        print("[INFO] *_temp 형태의 온도 컬럼을 찾지 못했습니다.")

    # ---- Memory Utilization ----
    # 1) 퍼센트 직접 제공
    mem_pct_cols = [c for c in df.columns if re.search(r"(mem_used_pct|mem.*util|memory.*util)", str(c), re.I)]
    mem_pct_nums = ensure_numeric(df, mem_pct_cols)

    mem_util = None
    if mem_pct_nums:
        # 여러 개면 평균
        mem_util = df[mem_pct_nums].mean(axis=1)
    else:
        # 2) used/total로 계산
        used_cols = [c for c in df.columns if re.search(r"(mem.*used|memory_used)", str(c), re.I)]
        total_cols = [c for c in df.columns if re.search(r"(mem.*total|memory_total)", str(c), re.I)]
        if used_cols and total_cols:
            used_num = ensure_numeric(df, [used_cols[0]])[0]
            total_num = ensure_numeric(df, [total_cols[0]])[0]
            # 0 나눗셈 방지
            with np.errstate(divide="ignore", invalid="ignore"):
                mem_util = (df[used_num] / df[total_num]) * 100.0

    if mem_util is not None:
        plot_series(x, mem_util.rolling(5, min_periods=1).mean(), "Memory Utilization", "Percent")
    else:
        print("[INFO] 메모리 퍼센트 또는 used/total 컬럼을 찾지 못했습니다.")

    # 요약 출력(선택)
    print({
        "time_column_found": time_col_raw,
        "time_column_used": time_col,
        "time_is_datetime": is_dt,
        "cpu_cols_used": cpu_cols,
        "temp_cols_used": temp_cols,
        "mem_pct_cols_used": mem_pct_cols
    })

if __name__ == "__main__":
    main()
