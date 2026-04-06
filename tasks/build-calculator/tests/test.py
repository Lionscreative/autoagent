"""Score mortgage calculator — preview + file content."""
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

# 2. INPUT FIELDS (2.5 pts)
check("price" in content or "home" in content or "loan amount" in content, 0.5, "Home price input")
check("down payment" in content or "downpayment" in content, 0.5, "Down payment input")
check("interest" in content or "rate" in content, 0.5, "Interest rate input")
check("15" in content and "30" in content, 0.5, "Loan term options (15/30)")
check("input" in content or "type=\"number\"" in content or "type=\"range\"" in content, 0.5, "Has input elements")

# 3. RESULTS OUTPUT (2 pts)
check("monthly" in content and "payment" in content, 1.0, "Shows monthly payment")
check("total interest" in content or "total_interest" in content or "totalinterest" in content, 1.0, "Shows total interest")

# 4. INTERACTIVITY (2 pts)
check("usestate" in code or "setstate" in code, 1.0, "Uses React state (useState)")
check("onchange" in code or "onclick" in code or "onsubmit" in code, 1.0, "Has event handlers")

# 5. AMORTIZATION & DESIGN (1.5 pts)
check("amortization" in content or "schedule" in content or "breakdown" in content, 0.75, "Amortization section")
check(len(file_list) >= 3, 0.25, f"Created {len(file_list)} files")
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive design")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
