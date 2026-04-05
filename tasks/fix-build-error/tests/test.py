"""Verify build errors were fixed."""
import os
import subprocess

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)

score = 0.0
max_score = 3.0
details = []


def check(condition, points, desc):
    global score
    if condition:
        score += points
        details.append(f"PASS ({points}): {desc}")
    else:
        details.append(f"FAIL (0/{points}): {desc}")


# 1. Build passes (critical)
try:
    result = subprocess.run(["npm", "run", "build"], cwd="/project",
                            capture_output=True, text=True, timeout=120)
    build_ok = result.returncode == 0
except Exception:
    build_ok = False

check(build_ok, 2.0, "npm run build passes")

# 2. Page still exists and has content
page = "/project/app/page.tsx"
if os.path.exists(page):
    c = open(page).read()
    check(len(c) > 50, 0.5, "Page has content")
    # The broken import should be fixed — either removed or the component created
    missing_comp_file = "/project/components/missing.tsx"
    import_removed = "MissingComponent" not in c
    component_created = os.path.exists(missing_comp_file) or os.path.exists("/project/src/components/missing.tsx")
    check(import_removed or component_created, 0.5, "Broken import fixed (removed or component created)")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
