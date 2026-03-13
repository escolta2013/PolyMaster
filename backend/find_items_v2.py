import os

root = "."
for dirpath, dirnames, filenames in os.walk(root):
    if ".venv" in dirpath or "__pycache__" in dirpath or ".git" in dirpath:
        continue
    for filename in filenames:
        if filename.endswith(".py"):
            filepath = os.path.join(dirpath, filename)
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                    if ".items()" in content:
                        print(f"\n--- {filepath} ---")
                        lines = content.splitlines()
                        for i, line in enumerate(lines):
                            if ".items()" in line:
                                print(f"{i+1}: {line.strip()}")
            except:
                pass
