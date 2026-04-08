"""Score error-use-client-directive — reproduces 'use client directive must be placed before other expressions'."""
import os, json, re

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
score = 0.0
max_score = 10.0
details = []

def check(cond, pts, desc):
    global score
    if cond: score += pts; details.append(f"PASS ({pts}): {desc}")
    else: details.append(f"FAIL (0/{pts}): {desc}")

eval_data = json.loads(open("/tmp/eval_results.json").read()) if os.path.exists("/tmp/eval_results.json") else {}
preview = eval_data.get("preview", {})
publish = eval_data.get("publish", {})
prod_check = eval_data.get("prod_check", {})
file_contents_map = eval_data.get("file_contents_map", {})
code = eval_data.get("file_contents", "").lower()

# 1. Preview loads (2pt)
check(preview.get("homepage_ok"), 2.0, "Preview homepage loads")

# 2. Publish succeeds (3pt)
check(publish.get("success") is True or prod_check.get("prod_homepage_ok") is True, 3.0, "Publish succeeded")

# 3. 'use client' first non-comment line in quiz.tsx (2pt)
quiz_content = ""
for path, c in (file_contents_map.items() if isinstance(file_contents_map, dict) else []):
    if "quiz" in path.lower() and path.endswith(".tsx"):
        quiz_content = c; break
if not quiz_content:
    # Fallback: scan file_contents blob for quiz.tsx section
    m = re.search(r'quiz\.tsx[^\n]*\n(.{0,300})', eval_data.get("file_contents", ""), re.IGNORECASE | re.DOTALL)
    if m: quiz_content = m.group(1)
# Strip leading blank/comment lines
lines = [l for l in quiz_content.splitlines() if l.strip() and not l.strip().startswith("//") and not l.strip().startswith("/*")]
first = lines[0].strip().strip(";").strip() if lines else ""
check(first in ('"use client"', "'use client'"), 2.0, f"'use client' is first non-comment line (got: {first[:40]})")

# 4. useState + useEffect (2pt)
check("usestate" in code and "useeffect" in code, 2.0, "useState + useEffect present")

# 5. Efficient (1pt)
check(eval_data.get("tool_calls", 99) <= 60, 1.0, "Efficient")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
