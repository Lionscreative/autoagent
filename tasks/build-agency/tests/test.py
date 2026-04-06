"""Score agency portfolio — preview + file content."""
import os, json

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
file_list = eval_data.get("files", [])
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code

# 1. PREVIEW (2 pts)
check(preview.get("homepage_ok"), 2.0, "Homepage loads")

# 2. BRAND & SERVICES (2 pts)
check("pixel" in content and "code" in content, 1.0, "Brand name Pixel & Code Studio visible")
services = sum(1 for w in ["web design", "branding", "mobile app", "mobile dev"] if w in content)
check(services >= 2, 1.0, f"Services listed ({services}/3)")

# 3. MULTI-PAGE (2 pts)
pages_ok = preview.get("pages_ok", {})
about_exists = pages_ok.get("/about", False) or any("about/page" in f or "about.tsx" in f for f in file_list)
contact_exists = pages_ok.get("/contact", False) or any("contact/page" in f or "contact.tsx" in f for f in file_list)
check(about_exists, 1.0, "About page exists")
check(contact_exists, 1.0, "Contact page exists")

# 4. PROJECT GRID (2 pts)
check("grid" in code, 1.0, "Grid layout in code")
# Count project-like items (thumbnails, cards, portfolio items)
project_words = sum(1 for w in ["project", "portfolio", "work", "case study", "thumbnail"] if w in content)
check(project_words >= 1, 0.5, f"Project section ({project_words} matches)")
# Check for multiple items (6 requested)
check(code.count("project") >= 3 or code.count("card") >= 3 or code.count("portfolio") >= 2, 0.5, "Multiple project items")

# 5. DESIGN QUALITY (1 pt)
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive breakpoints")
check("nav" in code or "header" in code, 0.5, "Navigation present")

# 6. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
