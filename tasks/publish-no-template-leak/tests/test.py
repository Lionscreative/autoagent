"""Critical: verify app/page.tsx imports components (no template leak)."""
import os, json, re

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
score = 0.0
max_score = 10.0
details = []

def check(cond, pts, desc):
    global score
    if cond:
        score += pts
        details.append(f"PASS ({pts}): {desc}")
    else:
        details.append(f"FAIL (0/{pts}): {desc}")

eval_data = json.loads(open("/tmp/eval_results.json").read()) if os.path.exists("/tmp/eval_results.json") else {}
preview = eval_data.get("preview", {})
code = eval_data.get("file_contents", "")
html_preview = preview.get("homepage_html", "")

# 1. PREVIEW loads (1 pt)
check(preview.get("homepage_ok"), 1.0, "Preview homepage loads")

# 2. CRITICAL: must NOT contain template welcome (4 pts)
template_leak_in_code = "welcome to your app" in code.lower()
template_leak_in_preview = "welcome to your app" in html_preview.lower()
check(
    not template_leak_in_code and not template_leak_in_preview,
    4.0,
    "app/page.tsx is NOT 'Welcome to Your App' template",
)

# 3. Brand name visible (2 pts)
brand_in_code = "brew & co" in code.lower() or "brew co" in code.lower() or "brew and co" in code.lower()
brand_in_preview = "brew & co" in html_preview.lower() or "brew co" in html_preview.lower()
check(brand_in_code or brand_in_preview, 2.0, "Brand 'Brew & Co' visible")

# 4. Components imported in page.tsx (2 pts)
has_component_imports = bool(
    re.search(r'<Hero\b', code)
    or re.search(r'<Features\b', code)
    or re.search(r'<Footer\b', code)
    or re.search(r'<Testimonials\b', code)
)
check(has_component_imports, 2.0, "page.tsx renders custom components (<Hero/>, <Features/>, etc.)")

# 5. Efficiency (1 pt)
check(eval_data.get("tool_calls", 999) <= 80, 0.5, "Efficient (<=80 tool calls)")
check(eval_data.get("duration_ms", 999999) <= 600000, 0.5, "Completed in <10min")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
