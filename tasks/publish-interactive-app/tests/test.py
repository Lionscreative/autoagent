"""Score publish-interactive-app — preview + publish + production URL check."""
import os, json

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
publish = eval_data.get("publish", {})
prod_check = eval_data.get("prod_check", {})
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code

# 1. PREVIEW (1 pt)
check(preview.get("homepage_ok"), 1.0, "Preview homepage loads")

# 2. PUBLISH SUCCESS (3 pts) — KEY METRIC
check(publish.get("success") is True, 3.0, "Publish to Cloudflare Workers succeeded")

# 3. PRODUCTION URL WORKS (3 pts) — KEY METRIC
check(prod_check.get("prod_homepage_ok") is True, 3.0, "Production URL returns OK")

# 4. LOCALSTORAGE (1 pt)
check("localstorage" in code, 1.0, "Uses localStorage for persistence")

# 5. USESTATE + USEEFFECT (1 pt)
check("usestate" in code and "useeffect" in code, 1.0, "useState + useEffect present")

# 6. DARK THEME (0.5 pt)
dark = any(
    cls in code
    for cls in ["bg-black", "bg-neutral-900", "bg-neutral-950", "bg-gray-900", "bg-gray-950", "bg-zinc-900", "bg-zinc-950", "dark:"]
)
check(dark, 0.5, "Dark theme classes")

# 7. BRAND (0.5 pt)
check("dailystreak" in content, 0.5, "'DailyStreak' brand visible")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
