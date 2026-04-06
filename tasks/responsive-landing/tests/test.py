"""Score SaaS landing — preview + file content."""
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
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code

# 1. PREVIEW (2.5 pts)
check(preview.get("homepage_ok"), 2.0, "Homepage loads")
check(preview.get("homepage_length", 0) > 500 or len(code) > 2000, 0.5, "Rich content")

# 2. HERO (1.5 pts)
check("cloudsync" in content or "cloud sync" in content, 0.5, "Brand name")
check("free trial" in content or "get started" in content or "start" in content, 0.5, "CTA visible")
check("<h1" in content or "text-5xl" in content or "text-4xl" in content or "text-6xl" in content, 0.5, "Hero heading")

# 3. FEATURES (1.5 pts)
features = sum(1 for w in ["sync", "encrypt", "collaborat", "secure", "real-time", "team", "fast", "reliable"] if w in content)
check(features >= 2, 0.75, f"Feature keywords ({features})")
check("feature" in content or features >= 3, 0.75, "Features section")

# 4. PRICING (2 pts)
has_pricing = "$" in content or "pricing" in content or "€" in content or "/mo" in content
check(has_pricing, 1.0, "Pricing visible")
tiers = sum(1 for t in ["free", "pro", "enterprise", "starter", "business", "premium"] if t in content)
check(tiers >= 2, 1.0, f"Multiple tiers ({tiers})")

# 5. FOOTER (1 pt)
check("footer" in code or "privacy" in content or "terms" in content, 0.5, "Footer")
check("2026" in content or "©" in content or "copyright" in content, 0.5, "Copyright")

# 6. EFFICIENCY (1.5 pts)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast")
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
