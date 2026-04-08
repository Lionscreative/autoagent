"""Score error-missing-imports — reproduces 'Module not found' error pattern."""
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
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code
errors = json.dumps(eval_data.get("errors", [])).lower() + json.dumps(publish.get("errors", [])).lower() + json.dumps(publish.get("logs", "")).lower()

# 1. Preview loads (2pt)
check(preview.get("homepage_ok"), 2.0, "Preview homepage loads")

# 2. Publish succeeds (3pt) — KEY
check(publish.get("success") is True or prod_check.get("prod_homepage_ok") is True, 3.0, "Publish to Cloudflare Workers succeeded")

# 3. No "Can't resolve" in errors (2pt)
check("can't resolve" not in errors and "cannot find module" not in errors and "module not found" not in errors, 2.0, "No 'Module not found' errors")

# 4. Has 3 pricing tiers visible in code (2pt)
tier_markers = sum(1 for w in ["starter", "pro", "enterprise", "basic", "premium", "business"] if w in content)
check(tier_markers >= 3, 2.0, f"Has 3+ pricing tiers ({tier_markers} markers)")

# 5. Efficient (1pt)
check(eval_data.get("tool_calls", 99) <= 60, 1.0, "Efficient (<60 tool calls)")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
