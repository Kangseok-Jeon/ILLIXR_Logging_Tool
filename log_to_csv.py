import re
import pandas as pd
import os

# ================================================================================
# 1. Convert log file to csv, which means OpenVINS (VIO integrator) execution time 
# ================================================================================

# 로그 파일 경로
log_file = "/home/nokdujeon/kangseok/ILLIXR/build/nsys_log/20250904_201556/illixr.log"

# [TIME]: 숫자 ms for total 패턴
pattern = re.compile(r"\[TIME\]:\s*([\d\.]+)\s*ms\s*for\s*total")

# 추출 결과 저장 리스트
time_totals = []

# 로그 파일에서 값 추출
with open(log_file, "r") as f:
    for line in f:
        match = pattern.search(line)
        if match:
            # ms → ns 변환 (1 ms = 1e6 ns)
            ns_value = int(float(match.group(1)) * 1_000_000)
            time_totals.append(ns_value)

# DataFrame으로 변환 (컬럼 이름을 Duration (ns)로)
df = pd.DataFrame({"Duration (ns)": time_totals})

# CSV 파일로 저장
output_csv = "/home/nokdujeon/kangseok/ILLIXR/analyze/data/OpenVINS.csv"
df.to_csv(output_csv, index=False)

print(f"총 {len(time_totals)}개의 값이 추출되어 {output_csv}에 저장되었습니다.")

# ================================================================================
# 2. Split NVTX range trace data into separate CSV files
# ================================================================================

# 입력 CSV (nsys stats --report nvtx-range-trace --format csv 결과물)
input_csv = "/home/nokdujeon/kangseok/ILLIXR/build/nsys_log/20250904_201556/illixr_nvtx_pushpop_trace.csv"
output_dir = "/home/nokdujeon/kangseok/ILLIXR/analyze/data"  # 결과 저장 폴더

os.makedirs(output_dir, exist_ok=True)

# CSV 읽기
df = pd.read_csv(input_csv)

# 필요한 컬럼만 사용
df = df[["Name", "Duration (ns)"]].copy()

# 1) 먼저 제외할 항목부터 필터링 (원본 Name 기준, 대소문자 무시)
exclude_mask = (
    df["Name"].str.contains(r"record_command_buffer", case=False, na=False) |
    df["Name"].str.contains(r"get fast pose", case=False, na=False)
)
df = df[~exclude_mask]

# 2) 그 다음 Name 정리: 맨 앞 ":" 제거 후, 첫 ":" 이후 전부 제거
def clean_name(name: str) -> str:
    name = name.lstrip(":")
    if ":" in name:
        name = name.split(":", 1)[0]
    return name.strip()

df["Name"] = df["Name"].apply(clean_name)

# 3) NVTX Name별로 CSV 저장 (100줄 이상만)
def safe_filename(s: str) -> str:
    # 파일명 안전화: 영문/숫자/언더스코어/하이픈만 유지
    s = re.sub(r"[^\w\-]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "unnamed"

for name, group in df.groupby("Name"):
    if len(group) >= 100:
        output_csv = os.path.join(output_dir, f"{safe_filename(name)}.csv")
        group[["Duration (ns)"]].to_csv(output_csv, index=False)
        print(f"{name} ({len(group)} rows) → {output_csv} 저장 완료")
    else:
        print(f"{name} ({len(group)} rows) → 저장 생략 (100 미만)")