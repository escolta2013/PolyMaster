import re
from pathlib import Path

log_dir = Path("logs")
log_files = list(log_dir.glob("autonomous*.log"))

total_hits = 0
total_misses = 0
total_errors = 0

print(f"Scanning {len(log_files)} log files...")

for log_path in log_files:
    try:
        content = log_path.read_text(encoding="utf-8", errors="replace")
        
        hits = len(re.findall(r"Cache HIT", content))
        misses = len(re.findall(r"Cache STORED", content))
        errors = len(re.findall(r"AttributeError: 'str' object has no attribute 'items'", content))
        
        total_hits += hits
        total_misses += misses
        total_errors += errors
    except Exception as e:
        print(f"Error reading {log_path}: {e}")

print(f"\n--- TOTAL STATS (Last ~15h across all logs) ---")
print(f"TOTAL_CACHE_HITS: {total_hits}")
print(f"TOTAL_CACHE_MISSES (New AI Calls): {total_misses}")
print(f"TOTAL_ATTRIBUTE_ERRORS: {total_errors}")

# Current Budget check
current_log = log_dir / "autonomous.log"
if current_log.exists():
    content = current_log.read_text(encoding="utf-8", errors="replace")
    budget_matches = re.findall(r"(\d+)/300 calls today", content)
    if budget_matches:
        print(f"CURRENT_BUDGET_USAGE (Today): {budget_matches[-1]}/300")
    else:
        print("Budget usage not found in current log.")
