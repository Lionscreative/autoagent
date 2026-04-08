"""Score error-unterminated-strings — reproduces 'Unterminated string constant'."""
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
code = eval_data.get("file_contents", "")
code_l = code.lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code_l
errors = (json.dumps(eval_data.get("errors", [])) + json.dumps(publish.get("errors", [])) + str(publish.get("logs", ""))).lower()

# 1. Preview loads (3pt)
check(preview.get("homepage_ok"), 3.0, "Preview homepage loads")

# 2. Publish succeeds (3pt) — KEY
check(publish.get("success") is True or prod_check.get("prod_homepage_ok") is True, 3.0, "Publish succeeded (no string break)")

# 3. 5 testimonials in code (2pt)
testimonial_markers = code_l.count("testimonial") + code_l.count("quote")
has_grid = "grid" in code_l
check(testimonial_markers >= 3 or content.count("role") >= 3, 2.0, "Has testimonials structure")

# 4. Apostrophes/quotes rendered (1pt)
check("&apos;" in code or "&quot;" in code or "\\'" in code or '\\"' in code or "'" in code, 1.0, "Escaped quotes present")

# 5. Efficient (1pt)
check(eval_data.get("tool_calls", 99) <= 60, 1.0, "Efficient")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
