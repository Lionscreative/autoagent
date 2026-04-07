"""Score publish-image-heavy — preview + publish + production URL check."""
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
file_list = eval_data.get("files", [])
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code

# 1. PREVIEW (1 pt)
check(preview.get("homepage_ok"), 1.0, "Preview homepage loads")

# 2. PUBLISH SUCCESS (3 pts) — KEY METRIC
check(publish.get("success") is True, 3.0, "Publish to Cloudflare Workers succeeded")

# 3. PRODUCTION URL WORKS (3 pts) — KEY METRIC
check(prod_check.get("prod_homepage_ok") is True, 3.0, "Production URL returns OK")

# 4. IMAGES IN CODE (1 pt)
has_images = (
    "<img" in content
    or "next/image" in code
    or 'from "next/image"' in code
    or "unsplash" in content
)
check(has_images, 1.0, "Has image elements (img/Image/Unsplash)")

# 5. ABOUT + CONTACT PAGES (1 pt)
pages_ok = preview.get("pages_ok", {})
about_exists = pages_ok.get("/about", False) or any("about/page" in f for f in file_list)
contact_exists = pages_ok.get("/contact", False) or any("contact/page" in f for f in file_list)
check(about_exists and contact_exists, 1.0, "About + contact pages exist")

# 6. BRAND (0.5 pt)
check("maya chen" in content or "maya" in content, 0.5, "Brand 'Maya Chen' visible")

# 7. EFFICIENCY (0.5 pt)
check(eval_data.get("tool_calls", 99) <= 60, 0.5, "Efficient tool usage")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f:
    f.write(str(final))
