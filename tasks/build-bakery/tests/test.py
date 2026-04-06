"""Score bakery website — preview + file content."""
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

# 2. BRAND & IDENTITY (2 pts)
check("au pain dor" in content or "pain doré" in content or "pain dore" in content, 1.0, "Bakery name visible")
check("lyon" in content, 1.0, "Location Lyon visible")

# 3. PRODUCTS (2 pts)
products = sum(1 for w in ["pain", "bread", "viennoiserie", "croissant", "pâtisserie", "patisserie", "pastry", "baguette", "artisan"] if w in content)
check(products >= 2, 1.0, f"Products listed ({products} matches)")
product_categories = sum(1 for w in ["pain", "viennoiserie", "pâtisserie", "patisserie"] if w in content)
check(product_categories >= 2, 1.0, f"Product categories ({product_categories}/3)")

# 4. HOURS (2 pts)
check("6h30" in content or "6:30" in content or "06:30" in content or "06h30" in content, 1.0, "Opening time visible")
check("lundi" in content or "monday" in content or "fermé" in content or "closed" in content or "mardi" in content or "tuesday" in content, 1.0, "Schedule/closed day visible")

# 5. FRENCH CONTENT (1 pt)
french_words = sum(1 for w in ["boulangerie", "artisanal", "notre", "nos", "horaires", "bienvenue", "accueil"] if w in content)
check(french_words >= 1, 1.0, f"French content ({french_words} words)")

# 6. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
