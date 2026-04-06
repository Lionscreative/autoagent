"""Score restaurant — preview + file content."""
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

# 1. PREVIEW (3 pts)
check(preview.get("homepage_ok"), 2.0, "Homepage loads")
check(preview.get("homepage_length", 0) > 500 or len(code) > 1000, 1.0, "Substantial content")

# 2. MENU PAGE (2 pts)
pages_ok = preview.get("pages_ok", {})
menu_exists = pages_ok.get("/menu", False) or any("menu/page" in f for f in file_list)
check(menu_exists, 1.0, "Menu page exists (preview or file)")
menu_items = sum(1 for w in ["pasta", "antipasti", "dessert", "tiramisu", "carbonara", "bruschetta"] if w in content)
check(menu_items >= 2, 0.5, f"Menu has food items ({menu_items})")
check("€" in content or "eur" in content, 0.5, "Prices in euros")

# 3. CONTENT (3 pts)
check("dolce vita" in content or "italian" in content or "restaurant" in content, 0.75, "Restaurant identity")
check("paris" in content or "rivoli" in content, 0.75, "Location visible")
check("reserve" in content or "réserv" in content or "book" in content or "table" in content, 0.75, "Reservation CTA")
check("nav" in code or "navbar" in code or "navigation" in code, 0.75, "Navigation present")

# 4. DESIGN (1 pt)
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive")
check(len(file_list) >= 5, 0.5, f"Created {len(file_list)} files")

# 5. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
