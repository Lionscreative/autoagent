"""Score elegant law firm site — typography, palette, and French content."""
import os, json, re

REWARD_PATH = "/logs/verifier/reward.txt"
os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
score = 0.0
max_score = 10.0
details = []

def check(cond, pts, desc):
    global score
    if cond: score += pts; details.append(f"PASS ({pts}): {desc}")
    else: details.append(f"FAIL (0/{pts}): {desc}")

def penalize(cond, pts, desc):
    global score
    if cond: score = max(0, score - pts); details.append(f"PENALTY (-{pts}): {desc}")

eval_data = json.loads(open("/tmp/eval_results.json").read()) if os.path.exists("/tmp/eval_results.json") else {}
preview = eval_data.get("preview", {})
file_list = eval_data.get("files", [])
code = eval_data.get("file_contents", "").lower()
html = preview.get("homepage_html", "").lower()
content = html + "\n" + code

# 1. PREVIEW (1 pt)
check(preview.get("homepage_ok"), 1.0, "Homepage loads")

# 2. CUSTOM FONTS (2.5 pts)
font_import = any(x in content for x in ["next/font/google", "next/font/local", "@import url('https://fonts.googleapis",
                                          "@import url(\"https://fonts.googleapis", "fonts.googleapis.com",
                                          "font-family:", "@font-face"])
check(font_import, 1.0, "Custom font import detected")

# Check for non-default fonts (serif or elegant sans)
elegant_fonts = ["playfair", "merriweather", "lora", "cormorant", "garamond", "bodoni",
                 "didot", "libre baskerville", "crimson", "noto serif", "dm serif",
                 "source serif", "eb garamond", "spectral", "bitter", "serif",
                 "georgia", "times", "palatino"]
has_elegant = any(f in content for f in elegant_fonts)
check(has_elegant, 1.0, "Elegant/serif font used")
# Penalize if ONLY Inter or system-ui (default template font)
only_default = "inter" in content and not has_elegant and "font-family" not in content.replace("font-family: inter", "")
penalize(only_default, 1.0, "Only default Inter font — no custom typography")

check(any(x in content for x in ["font-serif", "font-display", "font-heading"]) or has_elegant, 0.5, "Typography hierarchy")

# 3. NAVY/GOLD/CREAM PALETTE (2 pts)
navy_patterns = ["navy", "blue-900", "blue-950", "slate-900", "indigo-900", "#001", "#0a1", "#1a237e", "#0d1b2a"]
gold_patterns = ["gold", "amber-", "yellow-600", "yellow-700", "#d4a", "#c5a", "#b8860b", "#daa520", "#f5deb3"]
cream_patterns = ["cream", "amber-50", "yellow-50", "orange-50", "#fff8", "#faf0", "#fffdd0", "#f5f5dc", "ivory", "beige"]

has_navy = any(p in content for p in navy_patterns)
has_gold = any(p in content for p in gold_patterns)
has_cream = any(p in content for p in cream_patterns)

check(has_navy, 0.75, "Navy color in palette")
check(has_gold, 0.75, "Gold color in palette")
check(has_cream or has_gold, 0.5, "Cream/warm accent in palette")

# 4. THREE PAGES (1.5 pts)
pages_ok = preview.get("pages_ok", {})
accueil = True  # homepage is accueil
expertises = (pages_ok.get("/expertises", False) or pages_ok.get("/nos-expertises", False) or
              any("expertise" in f for f in file_list) or "expertise" in content)
contact = (pages_ok.get("/contact", False) or any("contact" in f for f in file_list))
check(accueil, 0.5, "Accueil page exists")
check(expertises, 0.5, "Expertises page exists")
check(contact, 0.5, "Contact page exists")

# 5. FRENCH CONTENT & BRAND (1.5 pts)
french_words = sum(1 for w in ["avocat", "droit", "cabinet", "expertise", "juridique",
                                "contentieux", "conseil", "affaires", "travail", "famille",
                                "accueil", "contactez", "notre", "nos", "nous"] if w in content)
check("laurent" in content, 0.5, "Brand name 'Laurent' present")
check(french_words >= 3, 0.5, f"French content ({french_words} words)")
check(french_words >= 6, 0.5, f"Rich French content ({french_words} words)")

# 6. PROFESSIONAL DESIGN (1 pt)
spacing = sum(1 for s in ["py-16", "py-20", "py-24", "py-32", "px-8", "px-12", "px-16",
                           "space-y-8", "space-y-12", "gap-8", "gap-12"] if s in content)
check(spacing >= 2, 0.5, f"Generous spacing ({spacing} instances)")
check(any(x in content for x in ["border-b", "divide-", "separator", "border-t"]) or
      any(x in content for x in ["tracking-wide", "tracking-wider", "uppercase", "leading-relaxed"]),
      0.5, "Refined typographic details")

# PENALTIES
penalize(not font_import and not has_elegant, 1.5, "No custom font at all — core requirement")
penalize(french_words == 0, 1.0, "No French content — instruction was in French")

final = round(min(score, max_score) / max_score, 3)
print("\n".join(details))
print(f"\nTotal: {score}/{max_score} = {final}")
with open(REWARD_PATH, "w") as f: f.write(str(final))
