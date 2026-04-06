"""Score blog website — preview + file content."""
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
check("morning brew" in content, 1.0, "Brand name The Morning Brew visible")

# 3. ARTICLES (2 pts)
# Look for article-like structures (titles, cards, posts)
article_words = sum(1 for w in ["article", "post", "blog", "read more", "read article"] if w in content)
check(article_words >= 1, 0.5, f"Article section present ({article_words} matches)")
# Check for coffee-related article content
coffee_words = sum(1 for w in ["coffee", "brew", "espresso", "latte", "roast", "bean", "barista", "cafe", "cappuccino"] if w in content)
check(coffee_words >= 2, 1.0, f"Coffee-themed content ({coffee_words} matches)")
# Check for multiple articles (3 requested)
check(code.count("article") >= 2 or code.count("post") >= 2 or code.count("card") >= 3 or code.count("<h2") >= 3 or code.count("<h3") >= 3, 0.5, "Multiple articles visible")

# 4. ABOUT PAGE (1 pt)
pages_ok = preview.get("pages_ok", {})
about_exists = pages_ok.get("/about", False) or any("about/page" in f or "about.tsx" in f for f in file_list)
check(about_exists, 1.0, "About page exists")

# 5. NEWSLETTER FORM (1.5 pts)
check("newsletter" in content or "subscribe" in content or "signup" in content or "sign up" in content, 0.75, "Newsletter section present")
check("email" in content and ("input" in code or "form" in code), 0.75, "Email input/form for newsletter")

# 6. MINIMALIST DESIGN (1.5 pts)
check(any(bp in code for bp in ["sm:", "md:", "lg:"]), 0.5, "Responsive breakpoints")
# Minimalist = clean colors, good typography
check(any(w in code for w in ["max-w-", "prose", "mx-auto", "container"]) , 0.5, "Clean layout (max-width/container)")
check("nav" in code or "header" in code, 0.5, "Navigation present")

# 7. EFFICIENCY (1 pt)
check(eval_data.get("tool_calls", 99) <= 50, 0.5, "Efficient tool usage")
check(eval_data.get("duration_ms", 999999) <= 300000, 0.5, "Fast execution")

final = round(score / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
