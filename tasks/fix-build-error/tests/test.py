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
    # Should NOT have the original broken import
    check("MissingComponent" not in c or "missing" not in c.split("import")[0] if "import" in c else True,
          0.5, "Broken import removed or fixed")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
