"""Verify contact page was added without breaking existing code."""
import os
import subprocess

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)

score = 0.0
max_score = 5.0
details = []


def check(condition, points, desc):
    global score
    if condition:
        score += points
        details.append(f"PASS ({points}): {desc}")
    else:
        details.append(f"FAIL (0/{points}): {desc}")


# 1. Build passes
try:
    result = subprocess.run(["npm", "run", "build"], cwd="/project",
                            capture_output=True, text=True, timeout=120)
    build_ok = result.returncode == 0
except Exception:
    build_ok = False

check(build_ok, 2.0, "npm run build passes")

# 2. Contact page exists with form
contact = "/project/app/contact/page.tsx"
check(os.path.exists(contact), 0.5, "Contact page exists")
if os.path.exists(contact):
    c = open(contact).read()
    check("form" in c.lower() or "<form" in c, 0.5, "Has form element")
    check("input" in c.lower(), 0.25, "Has input fields")
    check("Acme" in c or "acme" in c, 0.25, "Has company info")
    check("contact@acme" in c or "(555)" in c, 0.25, "Has contact details")

# 3. Homepage was NOT modified (critical)
try:
    result = subprocess.run(["md5sum", "app/page.tsx"], cwd="/project",
                            capture_output=True, text=True)
    current_hash = result.stdout.strip()
    original_hash = open("/tmp/homepage_hash.txt").read().strip()
    homepage_preserved = current_hash == original_hash
except Exception:
    homepage_preserved = False

check(homepage_preserved, 1.0, "Homepage was NOT modified (preserved existing work)")

# 4. Tailwind used
if os.path.exists(contact):
    c = open(contact).read()
    check("className" in c, 0.25, "Uses Tailwind classes")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
