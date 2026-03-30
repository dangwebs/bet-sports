#!/usr/bin/env python3
import os
import re
import sys

# Calculate path relative to this script to avoid hardcoded long literals
p = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "backend",
        "src",
        "domain",
        "services",
        "statistics_service.py",
    )
)
with open(p, "r", encoding="utf-8") as f:
    s = f.read()
start = s.find("aliases = {")
if start == -1:
    print("ALIASES_NOT_FOUND")
    sys.exit(1)
obr = s.find("{", start)
# find matching closing brace
depth = 0
i = obr
end = -1
while i < len(s):
    c = s[i]
    if c == "{":
        depth += 1
    elif c == "}":
        depth -= 1
        if depth == 0:
            end = i
            break
    i += 1
if end == -1:
    print("NO_MATCHING_BRACE")
    sys.exit(1)
block = s[obr : end + 1]
lines = block.splitlines()
kp = re.compile(r'^\s*"([^"]+)"\s*:\s*"([^"]+)"\s*,')
pre = s[:obr]
start_line = pre.count("\n") + 1
keys = {}
for idx, line in enumerate(lines, start=start_line):
    m = kp.match(line)
    if m:
        k = m.group(1)
        v = m.group(2)
        keys.setdefault(k, []).append({"value": v, "line": idx, "text": line.strip()})

safe = []
conflicts = []
for k, occ in keys.items():
    if len(occ) > 1:
        vals = {o["value"] for o in occ}
        if len(vals) == 1:
            safe.append({"key": k, "value": occ[0]["value"], "occurrences": occ})
        else:
            conflicts.append({"key": k, "values": list(vals), "occurrences": occ})

print("SAFE_DUPLICATES_COUNT:", len(safe))
for item in sorted(safe, key=lambda x: x["key"]):
    print("SAFE", item["key"], "=>", item["value"])
    for o in item["occurrences"]:
        print("  LINE", o["line"], o["text"])
print("CONFLICTS_COUNT:", len(conflicts))
for item in sorted(conflicts, key=lambda x: x["key"]):
    print("CONFLICT", item["key"], "VALUES", item["values"])
    for o in item["occurrences"]:
        print("  LINE", o["line"], o["text"])
