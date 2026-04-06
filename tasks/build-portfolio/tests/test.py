"""Score portfolio — preview + file content (handles client-side rendering)."""
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
# Combined source code — catches content that "use client" hides from SSR HTML
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
# Search both HTML and source code for content
content = html + "\n" + code

# 1. PREVIEW (3 pts)
check(preview.get("homepage_ok"), 2.0, "Homepage loads in preview")
check(preview.get("homepage_length", 0) > 500 or len(code) > 1000, 1.0, "Has substantial content")

# 2. PAGES EXIST (2 pts) — check both preview AND file list
pages_ok = preview.get("pages_ok", {})
about_exists = pages_ok.get("/about", False) or any("about/page" in f for f in file_list)
contact_exists = pages_ok.get("/contact", False) or any("contact/page" in f for f in file_list)
check(about_exists, 1.0, "About page exists (preview or file)")
check(contact_exists, 1.0, "Contact page exists (preview or file)")

# 3. CONTENT (3 pts) — check in source code too (not just SSR HTML)
check("sarah" in content or "photographer" in content or "portfolio" in content,
      0.75, "Relevant content (photographer/portfolio/Sarah)")
check("gallery" in content or "photo" in content or "image" in content or "work" in content,
      0.75, "Gallery/photo section in code")
check("<h1" in content or "text-5xl" in content or "text-4xl" in content or "text-6xl" in content,
      0.75, "Has hero heading (h1 or large text)")
check("wedding" in content or "portrait" in content or "event" in content,
      0.75, "Lists photography services")

# 4. DESIGN QUALITY (1 pt) — check source code for Tailwind patterns
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive breakpoints")
check("hover:" in code or "transition" in code, 0.5, "Interactive states")

# 5. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Completed in <5min")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
