"""Score the portfolio website based on what the USER sees (preview + files)."""
import os
import json

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)

score = 0.0
max_score = 10.0
details = []


def check(condition, points, desc):
    global score
    if condition:
        score += points
        details.append(f"PASS ({points}): {desc}")
    else:
        details.append(f"FAIL (0/{points}): {desc}")


# Load eval results from the agent (preview checks + file list)
eval_data = {}
if os.path.exists("/tmp/eval_results.json"):
    eval_data = json.loads(open("/tmp/eval_results.json").read())

preview = eval_data.get("preview", {})
file_list = eval_data.get("files", [])

# === 1. PREVIEW WORKS (4 points) — what the user actually sees ===
check(preview.get("homepage_ok", False), 3.0, "Homepage loads in preview (HTTP 200)")
check(preview.get("homepage_length", 0) > 1000, 1.0, "Homepage has substantial HTML (>1000 chars)")

# === 2. PAGES EXIST (2 points) ===
pages_ok = preview.get("pages_ok", {})
about_ok = pages_ok.get("/about", False)
contact_ok = pages_ok.get("/contact", False)
check(about_ok, 1.0, "About page loads in preview")
check(contact_ok, 1.0, "Contact page loads in preview")

# === 3. CONTENT QUALITY from homepage HTML (2 points) ===
html = preview.get("homepage_html", "")
html_lower = html.lower()

check("sarah" in html_lower or "photographer" in html_lower or "portfolio" in html_lower,
      0.5, "Homepage has relevant content (photographer/portfolio)")
check("gallery" in html_lower or "photo" in html_lower or "work" in html_lower or "image" in html_lower,
      0.5, "Homepage has gallery/photo section")
# Check for a compelling hero section
has_hero = any(tag in html_lower for tag in ["<h1", "<hero", "hero"])
check(has_hero, 0.5, "Homepage has hero/heading section")
# No broken content
no_error = "error" not in html_lower[:500] and "not found" not in html_lower[:500]
check(no_error, 0.5, "No error messages visible on homepage")

# === 4. FILES CREATED (1 point) ===
has_components = sum(1 for f in file_list if "component" in f.lower() or f.endswith(".tsx"))
check(has_components >= 3, 0.5, "Created 3+ component files")
check(len(file_list) >= 5, 0.5, "Created 5+ total files")

# === 5. EFFICIENCY (1 point) ===
tool_calls = eval_data.get("tool_calls", 0)
duration_s = eval_data.get("duration_ms", 999999) / 1000
check(tool_calls <= 50, 0.5, f"Efficient: {tool_calls} tool calls (<=50)")
check(duration_s <= 300, 0.5, f"Fast: {duration_s:.0f}s (<=300s)")

# If no eval results at all, fall back to checking local files
if not eval_data:
    details.append("WARNING: No eval_results.json — agent may not be using API mode")
    # Check if local files exist as fallback
    for root, _, files in os.walk("/project/app"):
        for f in files:
            if f.endswith(".tsx"):
                score += 0.1
                break

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
