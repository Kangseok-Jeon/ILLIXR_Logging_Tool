# convert nsys-rep data to understandable format
import re
import pandas as pd

# 로그 파일 경로
log_file = "illixr_20250904_201556.log"

# [TIME]: 숫자 ms for total 패턴
pattern = re.compile(r"\[TIME\]:\s*([\d\.]+)\s*ms\s*for\s*total")

# 추출 결과 저장 리스트
time_totals = []

# 로그 파일에서 값 추출
with open(log_file, "r") as f:
    for line in f:
        match = pattern.search(line)
        if match:
            time_totals.append(float(match.group(1)))

# DataFrame으로 변환
df = pd.DataFrame({"total_time_ms": time_totals})

# CSV 파일로 저장
output_csv = "time_totals.csv"
df.to_csv(output_csv, index=False)

print(f"총 {len(time_totals)}개의 값이 추출되어 {output_csv}에 저장되었습니다.")
