"""Score fitness website — preview + file content."""
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

# 2. BRAND NAME (1 pt)
check("fitwithmike" in content or "fit with mike" in content or "fitwithmike" in content, 1.0, "Brand name FitWithMike visible")

# 3. SERVICES (2 pts)
services = sum(1 for w in ["1-on-1", "one-on-one", "personal", "coaching", "1 on 1"] if w in content)
check(services >= 1, 0.7, f"1-on-1 coaching listed ({services} matches)")
check("group" in content and ("class" in content or "session" in content or "training" in content), 0.7, "Group classes listed")
check("online" in content and ("program" in content or "coaching" in content or "training" in content), 0.6, "Online programs listed")

# 4. PRICING (2 pts)
check("50" in content, 0.7, "$50/session price visible")
check("200" in content, 0.7, "$200/month unlimited price visible")
check("99" in content, 0.6, "$99/month online price visible")

# 5. CTA / BOOKING (1 pt)
cta_words = sum(1 for w in ["book", "start", "join", "sign up", "get started", "contact", "free", "trial", "schedule"] if w in content)
check(cta_words >= 1, 1.0, f"CTA/booking element ({cta_words} matches)")

# 6. DESIGN QUALITY (1 pt)
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive breakpoints")
check(len(file_list) >= 3, 0.5, f"Created {len(file_list)} files")

# 7. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
