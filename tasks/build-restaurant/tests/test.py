"""Verify the restaurant website was built correctly."""
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

# 2. Homepage content
homepage = "/project/app/page.tsx"
if os.path.exists(homepage):
    c = open(homepage).read()
    check(len(c) > 200, 0.5, "Homepage has substantial content")
    check("Dolce Vita" in c or "dolce vita" in c.lower(), 0.25, "Restaurant name present")
    check("Paris" in c or "Rivoli" in c, 0.25, "Address/location present")
    check("Reserve" in c or "reserve" in c or "Réserv" in c, 0.25, "CTA button present")

# 3. Menu page
menu = "/project/app/menu/page.tsx"
check(os.path.exists(menu), 0.5, "Menu page exists")
if os.path.exists(menu):
    c = open(menu).read()
    check("€" in c or "EUR" in c or "euro" in c.lower(), 0.25, "Prices in euros")
    # Check for categories
    cats = sum(1 for cat in ["Antipasti", "Pasta", "Dessert", "antipasti", "pasta", "dessert"]
               if cat in c)
    check(cats >= 2, 0.25, "At least 2 menu categories")

# 4. Navigation in layout
layout = "/project/app/layout.tsx"
if os.path.exists(layout):
    c = open(layout).read()
    check("menu" in c.lower() or "Menu" in c, 0.25, "Nav links to menu")
    check("Dolce" in c or "nav" in c.lower(), 0.25, "Layout has navigation")

# 5. Tailwind usage
tailwind_count = 0
for root, _, files in os.walk("/project/app"):
    for f in files:
        if f.endswith(".tsx"):
            content = open(os.path.join(root, f)).read()
            if "className" in content:
                tailwind_count += 1
check(tailwind_count >= 2, 0.25, "Tailwind used across files")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
