import re
import pandas as pd
from datetime import datetime
from pathlib import Path

# 사용자 입력
interval_ms = int(input("몇 ms 파일을 분석하시겠습니까? (예: 1, 10, 100): "))
PATH = Path("C:/Users/study/nsys_profile/tegra_log")

# 경로 및 파일명 구성
filename = f"txt/tegrastats_log_{interval_ms}ms.txt"
input_file = PATH / filename
output_file = PATH / f"csv/tegrastats_log_{interval_ms}ms.csv"

# 로그 파싱
data = []
with open(input_file, 'r') as f:
    for line in f:
        timestamp_match = re.search(r"\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}", line)
        if not timestamp_match:
            continue
        timestamp = datetime.strptime(timestamp_match.group(), "%m-%d-%Y %H:%M:%S")

        cpu_matches = re.findall(r"\d+%@\d+", line)
        cpu_vals = [int(x.split('%')[0]) for x in cpu_matches]
        cpu_avg = sum(cpu_vals) / len(cpu_vals) if cpu_vals else None

        ram = re.search(r"RAM (\d+)/", line)
        gpu = re.search(r"GR3D_FREQ (\d+)%", line)
        temp = re.search(r"cpu@(\d+\.\d+)C", line)
        power = re.search(r"VDD_IN (\d+)mW", line)

        data.append({
            "timestamp": timestamp,
            "cpu_avg": cpu_avg,
            "ram_used": int(ram.group(1)) if ram else None,
            "gpu_usage": int(gpu.group(1)) if gpu else None,
            "cpu_temp": float(temp.group(1)) if temp else None,
            "power_mW": int(power.group(1)) if power else None
        })

# 저장
df = pd.DataFrame(data)
df.to_csv(output_file, index=False)
print(f"✅ 변환 완료: {output_file}")
