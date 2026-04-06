"""Score expense tracker — preview + file content."""
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
check(preview.get("homepage_ok"), 1.5, "Homepage loads")
check(preview.get("homepage_length", 0) > 500 or len(code) > 1000, 0.5, "Substantial content")

# 2. ADD EXPENSE FORM (2.5 pts)
check("amount" in content, 0.5, "Amount field")
check("date" in content or "type=\"date\"" in content, 0.5, "Date field")
check("category" in content, 0.5, "Category field")
categories_found = sum(1 for c in ["food", "transport", "entertainment", "bills", "other"] if c in content)
check(categories_found >= 3, 0.5, f"Has expense categories ({categories_found}/5)")
check("input" in content or "type=\"number\"" in content, 0.5, "Has input elements")

# 3. SUMMARY & TOTALS (2 pts)
check("total" in content or "sum" in content, 1.0, "Shows total spent")
check("breakdown" in content or categories_found >= 3, 1.0, "Category breakdown visible")

# 4. VISUAL / CHART (1.5 pts)
chart_indicators = ["chart", "bar", "svg", "canvas", "width:", "height:", "recharts", "chart.js", "progress", "bg-"]
visual_found = sum(1 for c in chart_indicators if c in code)
check(visual_found >= 2, 1.0, f"Has visual/chart element ({visual_found} indicators)")
check("%" in code or "ratio" in code or "width" in code, 0.5, "Visual uses proportional sizing")

# 5. INTERACTIVITY & QUALITY (2 pts)
check("usestate" in code or "setstate" in code, 0.75, "Uses React state")
check("onchange" in code or "onclick" in code or "onsubmit" in code, 0.5, "Has event handlers")
check(len(file_list) >= 3, 0.25, f"Created {len(file_list)} files")
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive design")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
