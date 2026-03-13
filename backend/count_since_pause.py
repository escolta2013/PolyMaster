
import re
import os

log_files = [
    r"backend\logs\autonomous.2026-03-06_16-58-58_906152.log",
    r"backend\logs\autonomous.2026-03-07_20-48-20_332106.log",
    r"backend\logs\autonomous.log"
]

total_markets = 0
found_pause = False
pause_pattern = "Smart Money Tracker is DISABLED"
discovery_pattern = re.compile(r"Cycle Result: (\d+) Discovery markets analyzed")

for log_path in log_files:
    if not os.path.exists(log_path):
        continue
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if not found_pause:
                if pause_pattern in line:
                    found_pause = True
                continue
            
            match = discovery_pattern.search(line)
            if match:
                total_markets += int(match.group(1))

print(f"Total Discovery markets analyzed since pause: {total_markets}")
