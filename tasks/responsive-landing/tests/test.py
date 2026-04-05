"""Verify the SaaS landing page was built correctly."""
import os
import subprocess

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)

score = 0.0
max_score = 6.0
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

# 2. Page content analysis
page = "/project/app/page.tsx"
if not os.path.exists(page):
    details.append("FAIL: page.tsx not found")
else:
    c = open(page).read()
    check(len(c) > 500, 0.5, "Page has substantial content (>500 chars)")

    # Hero section
    check("CloudSync" in c or "cloudsync" in c.lower(), 0.25, "Brand name present")
    check("Sync" in c and "file" in c.lower(), 0.25, "Hero headline present")
    check("Free Trial" in c or "free trial" in c.lower() or "Start" in c, 0.25, "CTA button present")

    # Features
    features_found = sum(1 for f in ["Real-time", "Encryption", "Collaboration",
                                      "real-time", "encryption", "collaboration",
                                      "sync", "secure", "team"]
                         if f in c)
    check(features_found >= 3, 0.5, "At least 3 feature mentions")

    # Pricing
    check("$0" in c or "Free" in c, 0.25, "Free tier present")
    check("$12" in c or "$49" in c or "Pro" in c, 0.25, "Paid tiers present")
    check("Popular" in c or "popular" in c or "recommended" in c.lower(), 0.25, "Highlighted tier")

    # Footer
    check("Privacy" in c or "Terms" in c or "2026" in c or "©" in c, 0.25, "Footer present")

    # Responsive design (Tailwind breakpoints)
    responsive = sum(1 for bp in ["sm:", "md:", "lg:", "xl:"] if bp in c)
    check(responsive >= 2, 0.5, "Uses responsive breakpoints (sm:/md:/lg:)")

    # Grid usage
    check("grid" in c and "col" in c, 0.25, "Uses CSS grid for layout")

    # Full viewport hero
    check("min-h-screen" in c or "h-screen" in c or "100vh" in c, 0.25, "Full viewport hero")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
