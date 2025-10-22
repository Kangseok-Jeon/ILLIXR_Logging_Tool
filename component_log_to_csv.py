import re
import os
from pathlib import Path
import pandas as pd

# ======================================================================
# 설정
# ======================================================================
BASE_DIR = Path("/home/nokdujeon/kangseok/ILLIXR/build/logger")  # build/logger
ANALYZE_DIR = Path("/home/nokdujeon/kangseok/ILLIXR/analyze/data")
ANALYZE_DIR.mkdir(parents=True, exist_ok=True)

# ======================================================================
# 유틸
# ======================================================================
def subdirs(p: Path):
    return [d for d in p.iterdir() if d.is_dir()]

def latest_dir_by_mtime(p: Path) -> Path:
    subs = subdirs(p)
    return max(subs, key=lambda d: d.stat().st_mtime) if subs else p

def safe_filename(s: str) -> str:
    s = re.sub(r"[^\w\-]+", "_", str(s))
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unnamed"

def clean_name(name: str) -> str:
    name = str(name).lstrip(":")
    if ":" in name:
        name = name.split(":", 1)[0]
    return name.strip()

# ======================================================================
# 처리 대상: build/logger 내의 *_nsys 폴더 모두
# ======================================================================
apps = [d for d in subdirs(BASE_DIR) if d.name.endswith("_nsys")]
if not apps:
    raise SystemExit(f"[INFO] *_nsys 폴더가 없습니다: {BASE_DIR}")

summary = []

for app_dir in sorted(apps):
    app_name = app_dir.name.replace("_nsys", "")
    print(f"\n=== APP: {app_name} ({app_dir}) ===")

    # 최신 런 폴더 탐색 (예: build/logger/openxr_nsys/20250904_201556/)
    run_dir = latest_dir_by_mtime(app_dir)
    # 만약 바로 파일이 있는 구조면 run_dir 그대로, 아니면 하위 최신 폴더 한 번 더 확인
    log_file = run_dir / "illixr.log"
    nvtx_csv = run_dir / "illixr_nvtx_pushpop_trace.csv"
    if not log_file.exists() or not nvtx_csv.exists():
        # 하위에 한 단계 더 있을 수 있으니 한 번 더 최신 디렉토리 탐색
        run_dir2 = latest_dir_by_mtime(run_dir)
        log_file2 = run_dir2 / "illixr.log"
        nvtx_csv2 = run_dir2 / "illixr_nvtx_pushpop_trace.csv"
        if log_file2.exists():
            log_file = log_file2
        if nvtx_csv2.exists():
            nvtx_csv = nvtx_csv2
        run_dir = run_dir2

    print(f"[INFO] run_dir : {run_dir}")
    print(f"[INFO] illixr : {'OK' if log_file.exists() else 'MISSING'} -> {log_file}")
    print(f"[INFO] nvtx   : {'OK' if nvtx_csv.exists() else 'MISSING'} -> {nvtx_csv}")

    # -----------------------------
    # 1) illixr.log → OpenVINS total(ns)
    # -----------------------------
    ov_rows = 0
    if log_file.exists():
        pattern = re.compile(r"\[TIME\]:\s*([\d\.]+)\s*ms\s*for\s*total")
        time_totals = []
        with open(log_file, "r", errors="ignore") as f:
            for line in f:
                m = pattern.search(line)
                if m:
                    ns_value = int(float(m.group(1)) * 1_000_000)  # ms → ns
                    time_totals.append(ns_value)
        ov_df = pd.DataFrame({"Duration (ns)": time_totals})
        out_ov = ANALYZE_DIR / f"OpenVINS_{app_name}.csv"
        ov_df.to_csv(out_ov, index=False)
        ov_rows = len(ov_df)
        print(f"[OK] OpenVINS totals: {ov_rows} rows → {out_ov}")
    else:
        print("[SKIP] illixr.log 미존재")

    # -----------------------------
    # 2) NVTX range trace CSV 분리 저장
    # -----------------------------
    saved = 0
    skipped = 0
    if nvtx_csv.exists():
        df = pd.read_csv(nvtx_csv)
        # 필요한 컬럼만
        cols_needed = [c for c in ["Name", "Duration (ns)"] if c in df.columns]
        if len(cols_needed) < 2:
            print(f"[WARN] NVTX CSV에 필요한 컬럼이 없습니다: {nvtx_csv}")
        else:
            df = df[cols_needed].copy()

            # 제외 규칙
            exclude_mask = (
                df["Name"].astype(str).str.contains(r"record_command_buffer", case=False, na=False) |
                df["Name"].astype(str).str.contains(r"get fast pose", case=False, na=False)
            )
            df = df[~exclude_mask]

            # Name 정리
            df["Name"] = df["Name"].astype(str).apply(clean_name)

            # 저장
            for name, group in df.groupby("Name"):
                if len(group) >= 100:
                    out_csv = ANALYZE_DIR / f"{safe_filename(name)}_{app_name}.csv"
                    group[["Duration (ns)"]].to_csv(out_csv, index=False)
                    saved += 1
                else:
                    skipped += 1
            print(f"[OK] NVTX 분리 저장: saved={saved}, skipped(<100)={skipped}")
    else:
        print("[SKIP] NVTX CSV 미존재")

    summary.append({
        "app": app_name,
        "run_dir": str(run_dir),
        "openvins_rows": ov_rows,
        "nvtx_saved": saved,
        "nvtx_skipped": skipped
    })

# 요약 출력
print("\n=== SUMMARY ===")
for s in summary:
    print(s)
