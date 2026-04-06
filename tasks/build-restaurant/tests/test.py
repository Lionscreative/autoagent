"""Score the restaurant website based on what the USER sees."""
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
html = preview.get("homepage_html", "").lower()
pages_ok = preview.get("pages_ok", {})

# 1. PREVIEW (4 pts)
check(preview.get("homepage_ok"), 3.0, "Homepage loads in preview")
check(preview.get("homepage_length", 0) > 1000, 1.0, "Homepage has substantial HTML")

# 2. MENU PAGE (2 pts)
check(pages_ok.get("/menu", False), 1.5, "Menu page loads")
check("€" in html or "menu" in html or "pasta" in html or "antipasti" in html, 0.5, "Menu content visible")

# 3. CONTENT (2 pts)
check("dolce vita" in html or "restaurant" in html or "italian" in html, 0.5, "Restaurant name/type visible")
check("paris" in html or "rivoli" in html, 0.5, "Location visible")
check("reserve" in html or "réserv" in html or "book" in html, 0.5, "CTA/reservation visible")
check("<nav" in html or "nav" in html, 0.5, "Navigation visible")

# 4. FILES (1 pt)
file_list = eval_data.get("files", [])
check(len(file_list) >= 5, 0.5, f"Created {len(file_list)} files (>=5)")
check(any("menu" in f.lower() for f in file_list), 0.5, "Menu component/page created")

# 5. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Completed in <5min")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
