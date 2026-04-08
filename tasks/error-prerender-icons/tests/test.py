"""Score error-prerender-icons — reproduces 'Error occurred prerendering page /icon'."""
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
publish = eval_data.get("publish", {})
prod_check = eval_data.get("prod_check", {})
file_list = eval_data.get("files", [])
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code

# 1. Preview loads (2pt)
check(preview.get("homepage_ok"), 2.0, "Preview homepage loads")

# 2. Publish succeeds (4pt) — KEY
check(publish.get("success") is True or prod_check.get("prod_homepage_ok") is True, 4.0, "Publish succeeded (icon didn't crash)")

# 3. icon.tsx exists (1pt)
has_icon = any("icon.tsx" in f and "apple" not in f for f in file_list) or "app/icon" in code
check(has_icon, 1.0, "icon.tsx exists")

# 4. apple-icon.tsx exists (1pt)
has_apple = any("apple-icon" in f for f in file_list) or "apple-icon" in code
check(has_apple, 1.0, "apple-icon.tsx exists")

# 5. Brand 'NorthPeak' visible (1pt)
check("northpeak" in content, 1.0, "'NorthPeak' brand visible")

# 6. Efficient (1pt)
check(eval_data.get("tool_calls", 99) <= 60, 1.0, "Efficient")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
