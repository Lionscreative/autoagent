"""Score the SaaS landing page based on what the USER sees."""
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

# 1. PREVIEW (3 pts)
check(preview.get("homepage_ok"), 2.0, "Homepage loads in preview")
check(preview.get("homepage_length", 0) > 2000, 1.0, "Rich page (>2000 chars HTML)")

# 2. HERO (1.5 pts)
check("cloudsync" in html or "sync" in html, 0.5, "Brand name visible")
check("free trial" in html or "start" in html or "get started" in html, 0.5, "CTA visible")
check("<h1" in html, 0.5, "Has h1 heading")

# 3. FEATURES (1.5 pts)
features = sum(1 for w in ["sync", "encrypt", "collaborat", "secure", "real-time", "team"] if w in html)
check(features >= 2, 0.75, f"Feature keywords visible ({features})")
check("feature" in html or features >= 3, 0.75, "Features section present")

# 4. PRICING (2 pts)
has_pricing = "$" in html or "free" in html or "pricing" in html or "€" in html
check(has_pricing, 1.0, "Pricing visible")
tiers = sum(1 for t in ["free", "pro", "enterprise", "starter", "business"] if t in html)
check(tiers >= 2, 1.0, f"Multiple pricing tiers ({tiers})")

# 5. FOOTER (1 pt)
check("privacy" in html or "terms" in html or "footer" in html or "©" in html, 0.5, "Footer visible")
check("2026" in html or "©" in html or "copyright" in html, 0.5, "Copyright visible")

# 6. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Completed in <5min")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
