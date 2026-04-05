"""Verify the portfolio website was built correctly."""
import os
import subprocess
import sys

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)

score = 0.0
max_score = 5.0
details = []


def check(condition: bool, points: float, desc: str):
    global score
    if condition:
        score += points
        details.append(f"PASS ({points}): {desc}")
    else:
        details.append(f"FAIL (0/{points}): {desc}")


# 1. Build passes (most important)
try:
    result = subprocess.run(
        ["npm", "run", "build"],
        cwd="/project",
        capture_output=True,
        text=True,
        timeout=120,
    )
    build_ok = result.returncode == 0
except Exception as e:
    build_ok = False
    details.append(f"Build exception: {e}")

check(build_ok, 2.0, "npm run build passes")

# 2. Homepage exists and has content
homepage = "/project/app/page.tsx"
if os.path.exists(homepage):
    content = open(homepage).read()
    check(len(content) > 200, 0.5, "Homepage has substantial content")
    check("Sarah" in content or "sarah" in content, 0.25, "Homepage mentions Sarah")
    check("gallery" in content.lower() or "grid" in content.lower() or "photo" in content.lower(),
          0.25, "Homepage has gallery/photo section")
else:
    details.append("FAIL: Homepage not found")

# 3. About page exists
about = "/project/app/about/page.tsx"
check(os.path.exists(about), 0.5, "About page exists")
if os.path.exists(about):
    content = open(about).read()
    check("Wedding" in content or "wedding" in content or "Portrait" in content,
          0.25, "About page lists services")

# 4. Contact page exists with form
contact = "/project/app/contact/page.tsx"
check(os.path.exists(contact), 0.5, "Contact page exists")
if os.path.exists(contact):
    content = open(contact).read()
    check("form" in content.lower() or "input" in content.lower(),
          0.25, "Contact page has form elements")

# 5. Uses Tailwind classes
all_files = []
for root, dirs, files in os.walk("/project/app"):
    for f in files:
        if f.endswith(".tsx") or f.endswith(".ts"):
            all_files.append(os.path.join(root, f))

tailwind_usage = 0
for fp in all_files:
    content = open(fp).read()
    if "className" in content and ("flex" in content or "grid" in content or "bg-" in content):
        tailwind_usage += 1

check(tailwind_usage >= 2, 0.5, "Multiple files use Tailwind classes")

# Final score
final = round(score / max_score, 3)

print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")

with open(REWARD_PATH, "w") as f:
    f.write(str(final))
