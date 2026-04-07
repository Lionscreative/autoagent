"""
Shared verifier library for Sophie tasks.

Hybrid scoring:
  - HARD RULES (5 pts max): deterministic regex/string checks. Unhackable floor.
  - SOFT JUDGE (5 pts max): Groq Llama persona judge with 3 personas + anti-sycophancy anchor.

Total: 10 pts. Final reward written as 0.0-1.0 to /logs/verifier/reward.txt.

Import this from each task's tests/test.py:

    import sys
    sys.path.insert(0, "/tasks-sophie")  # Harbor mounts task dir
    from _verifier_lib import score_email

    score_email(
        expected_language="fr",
        required_terms=["marie", "dupont"],
        forbidden_greetings=["Salut Mon,", "Salut Chauffeur,"],
        personas=[...],
    )
"""

import json
import os
import re
import sys
from typing import Any

try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False

# Vercel proxy fallback — used when Groq is geo-blocked from local dev
EVAL_PROXY_URL = os.environ.get(
    "EVAL_PROXY_URL",
    "https://www.robot-speed.com/api/admin/eval/llm-judge",
)
EVAL_PROXY_SECRET = os.environ.get("EVAL_PROXY_SECRET", "").strip()

EVAL_PATH = "/tmp/eval_results.json"
REWARD_PATH = "/logs/verifier/reward.txt"

# ============================================================================
# REGEX CONSTANTS (language leak detection)
# ============================================================================

RE_CJK = re.compile(r'[\u4E00-\u9FFF\u3400-\u4DBF\u3000-\u303F]')
RE_ARABIC = re.compile(r'[\u0600-\u06FF\u0750-\u077F]')
RE_CYRILLIC = re.compile(r'[\u0400-\u04FF]')
RE_DEVANAGARI = re.compile(r'[\u0900-\u097F]')

# English verbs that leak into French/German emails from MiniMax M2.7
EN_LEAK_IN_FR = re.compile(
    r'\b(publish(es|ed|ing)?|search(es|ed|ing)?|exercises?|customers?|because|'
    r'without|already|their|about|should|would|could|have|website|content|'
    r'marketing(?!\b))\b',
    re.IGNORECASE,
)

# Spanish leaks
ES_LEAK = re.compile(r'\b(como|pero|tienen|tienes|tiene|parecido|mayoría|también)\b', re.IGNORECASE)

# Em-dashes and semicolons (Sophie anti-patterns)
RE_EM_DASH = re.compile(r'[—–]')
RE_SEMICOLON = re.compile(r';')

# Signature
RE_SIGNATURE = re.compile(r'Sophie\s*[·\-]\s*Customer Success\s*[·\-]\s*RobotSpeed', re.IGNORECASE)

# "cherche" / "tape" / "google" anti-pattern
FR_SEARCH_PATTERN = re.compile(r'\b(cherche(nt)?|tape(nt)?|qui googl|filtre(nt)?)\b', re.IGNORECASE)

# Banned greeting starters (business-name-as-firstname bug)
BAD_GREETING_WORDS = {
    "mon", "ma", "mes", "le", "la", "les", "l'", "the", "my", "our",
    "das", "der", "die", "support", "contact", "info", "hello", "admin",
    "sales", "team", "office", "veille", "conseil", "atelier", "studio",
    "animal",  # business names like "Animal Zen Attitude"
}


# ============================================================================
# HARD RULES (deterministic)
# ============================================================================

def strip_signature(body: str) -> str:
    """Remove the Sophie signature line so it doesn't interfere with language checks."""
    # Remove "Sophie · Customer Success · RobotSpeed" (with optional variants)
    return re.sub(
        r'Sophie\s*[·\-]\s*Customer Success\s*[·\-]\s*RobotSpeed',
        '',
        body,
        flags=re.IGNORECASE,
    )


def check_hard_rules(
    email: dict,
    expected_language: str,
    required_terms: list[str],
    forbidden_greetings: list[str],
) -> tuple[float, list[str]]:
    """Returns (hard_score_0_to_5, details_log).

    Hard rules are UNHACKABLE — they are the floor. Sophie cannot gain more
    than 5 pts from the LLM judge without also passing hard rules.
    """
    subject = email.get("subject", "") or ""
    body = email.get("body_text", "") or ""
    # Strip signature for language/format checks — "Customer Success" is the job title,
    # always in English, and shouldn't count as an English leak.
    body_no_sig = strip_signature(body)
    combined = f"{subject}\n{body_no_sig}"

    score = 0.0
    details = []

    def check(cond: bool, pts: float, desc: str):
        nonlocal score
        if cond:
            score += pts
            details.append(f"HARD PASS (+{pts}): {desc}")
        else:
            details.append(f"HARD FAIL (0/{pts}): {desc}")

    # 1. NO foreign scripts (1 pt)
    no_foreign_script = not (
        RE_CJK.search(combined)
        or RE_ARABIC.search(combined)
        or RE_CYRILLIC.search(combined)
        or RE_DEVANAGARI.search(combined)
    )
    check(no_foreign_script, 1.0, "No CJK/Arabic/Cyrillic/Devanagari characters")

    # 2. LANGUAGE correctness (1 pt) — always uses body_no_sig to exclude "Customer Success"
    if expected_language == "fr":
        # No English verb leaks
        en_match = EN_LEAK_IN_FR.search(body_no_sig)
        es_match = ES_LEAK.search(body_no_sig)
        lang_ok = en_match is None and es_match is None
        desc = "No English/Spanish leaks in French body"
        if en_match:
            desc += f" (found EN: '{en_match.group(0)}')"
        if es_match:
            desc += f" (found ES: '{es_match.group(0)}')"
        check(lang_ok, 1.0, desc)
    elif expected_language == "de":
        # No French/English greetings in German
        fr_leak = re.search(r'\b(bonjour|salut|merci|cordialement)\b', body_no_sig, re.IGNORECASE)
        check(fr_leak is None, 1.0, "No French leaks in German body")
    else:  # en
        # No French greetings in English
        fr_leak = re.search(r'\b(bonjour|salut|merci|cordialement)\b', body_no_sig, re.IGNORECASE)
        check(fr_leak is None, 1.0, "No French leaks in English body")

    # 3. NO em-dashes / semicolons (1 pt) — use body without signature
    no_dashes = not RE_EM_DASH.search(body_no_sig) and not RE_SEMICOLON.search(body_no_sig)
    check(no_dashes, 1.0, "No em-dashes or semicolons")

    # 4. GREETING correctness (1 pt)
    first_line = body.strip().split("\n")[0].strip() if body.strip() else ""
    first_line_lower = first_line.lower()

    # Check bad greetings
    has_bad_greeting = False
    for bad in forbidden_greetings:
        if body.startswith(bad):
            has_bad_greeting = True
            break

    # Check if greeting uses a known-bad first word
    if not has_bad_greeting:
        # Match "Salut Xxx," or "Hey Xxx," or "Hallo Xxx,"
        greeting_match = re.match(
            r'^(Salut|Hey|Hi|Bonjour|Hallo|Grüezi)\s+(\w+)\s*[,.]',
            first_line,
            re.IGNORECASE,
        )
        if greeting_match:
            greeted_name = greeting_match.group(2).lower()
            if greeted_name in BAD_GREETING_WORDS:
                has_bad_greeting = True
                details.append(f"  → bad greeted word: '{greeting_match.group(2)}'")

    check(not has_bad_greeting, 1.0, "Greeting does not use business/generic word")

    # 5. REQUIRED terms present (1 pt)
    content_lower = combined.lower()
    missing = [t for t in required_terms if t.lower() not in content_lower]
    check(
        len(missing) == 0,
        1.0,
        f"Required terms present ({len(required_terms)})" if not missing else f"Missing: {missing}",
    )

    return score, details


# ============================================================================
# SOFT JUDGE (Groq Llama persona)
# ============================================================================

JUDGE_PROMPT_TEMPLATE = """Tu es une vraie personne qui reçoit des cold emails commerciaux. Voici ton profil:

PROFIL:
{persona}

CONTEXTE:
- Tu reçois 20 à 50 cold emails par semaine.
- 99% d'entre eux finissent à la corbeille en 3 secondes.
- Tu réponds à MOINS DE 1 sur 30.
- Tu détestes les emails génériques, les flatteries creuses, les "j'ai regardé votre site" non-prouvés.
- Tu apprécies: une observation ULTRA spécifique sur ton business, une vraie question qui montre qu'on te comprend, de la valeur gratuite avant toute demande.

EMAIL REÇU:
Sujet: {subject}
Corps:
{body}

DEFAULT: would_reply = false. Trust signals = 2/10. Feels personal = 1/10.

Pour considérer would_reply = true, l'email DOIT avoir AU MOINS UN des critères suivants:
1. Mentionne quelque chose d'ULTRA spécifique sur le business (pas générique "vous êtes en Asie", mais un VRAI détail)
2. Pose une VRAIE question à laquelle tu as envie de répondre (pas "ça vous intéresse ?")
3. Apporte de la valeur AVANT de demander quoi que ce soit (un insight gratuit précis)

Sois IMPITOYABLE. Répondre yes par défaut c'est ce que font les juges LLMs sycophantes — fais mieux que ça.

Réponds STRICTEMENT en JSON:
{{
  "would_reply": true ou false,
  "reply_likelihood_pct": 0 à 100,
  "feels_personal_to_me": 0 à 10,
  "trust_signals": 0 à 10,
  "feels_like_ai_0_to_10": 0 à 10,
  "deal_breaker": "ce qui t'a fait delete (une phrase, ou null si tu réponds)",
  "what_worked": "ce qui a marché (ou null)"
}}
"""


def _call_judge_direct(api_key: str, prompt: str) -> str:
    """Call Groq directly. Raises on geo-block or error."""
    client = Groq(api_key=api_key)
    resp = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=400,
        response_format={"type": "json_object"},
    )
    return resp.choices[0].message.content or "{}"


def _call_judge_proxy(prompt: str) -> str:
    """Call the Vercel proxy endpoint. Used when Groq is geo-blocked locally."""
    if not HTTPX_AVAILABLE:
        raise RuntimeError("httpx not installed for proxy fallback")
    if not EVAL_PROXY_SECRET:
        raise RuntimeError("EVAL_PROXY_SECRET not set for proxy fallback")

    # The proxy uses generateText (not generateObject) so we need to extract JSON
    # from the response text. Append a JSON-only instruction to the prompt.
    full_prompt = prompt + "\n\nRéponds UNIQUEMENT avec un objet JSON valide (pas de markdown, pas d'explication)."

    resp = httpx.post(
        EVAL_PROXY_URL,
        headers={
            "Content-Type": "application/json",
            "X-Eval-Secret": EVAL_PROXY_SECRET,
        },
        json={
            "prompt": full_prompt,
            "model": "llama-3.3-70b-versatile",
            "temperature": 0.2,
            "max_tokens": 400,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data.get("content", "{}")

    # Strip markdown code fences if present
    content = re.sub(r'^```(?:json)?\s*', '', content.strip())
    content = re.sub(r'\s*```$', '', content.strip())
    return content


def run_persona_judge(
    email: dict,
    personas: list[str],
    judge_language: str = "fr",
) -> tuple[float, list[str]]:
    """Run 3 persona judges, average the scores.

    Tries Groq direct first; falls back to Vercel proxy if geo-blocked.
    Returns (soft_score_0_to_5, details_log).
    """
    details = []

    if not GROQ_AVAILABLE:
        details.append("JUDGE SKIPPED: groq library not installed")
        return 2.5, details

    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    use_proxy = False

    if not api_key:
        if EVAL_PROXY_SECRET:
            details.append("JUDGE: no GROQ_API_KEY, using Vercel proxy")
            use_proxy = True
        else:
            details.append("JUDGE SKIPPED: GROQ_API_KEY and EVAL_PROXY_SECRET both missing")
            return 2.5, details

    subject = email.get("subject", "") or ""
    body = email.get("body_text", "") or ""

    scores = []
    for i, persona in enumerate(personas):
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            persona=persona,
            subject=subject,
            body=body,
        )
        try:
            # Try direct Groq first (unless we already know it's blocked)
            if not use_proxy and api_key:
                try:
                    raw = _call_judge_direct(api_key, prompt)
                except Exception as direct_err:
                    # If geo-blocked or network error, switch to proxy for remaining personas
                    err_str = str(direct_err).lower()
                    if "access denied" in err_str or "network" in err_str or "403" in err_str:
                        if EVAL_PROXY_SECRET:
                            details.append(f"JUDGE {i+1}: Groq blocked, falling back to proxy")
                            use_proxy = True
                            raw = _call_judge_proxy(prompt)
                        else:
                            raise
                    else:
                        raise
            else:
                raw = _call_judge_proxy(prompt)

            judgment = json.loads(raw)

            would_reply = bool(judgment.get("would_reply", False))
            feels_personal = float(judgment.get("feels_personal_to_me", 0))
            trust = float(judgment.get("trust_signals", 0))
            feels_ai = float(judgment.get("feels_like_ai_0_to_10", 10))

            # Score 0-5:
            #   would_reply: 2.0 pts (binary)
            #   feels_personal / 10 * 1.5 pts
            #   trust / 10 * 1.0 pt
            #   (10 - feels_ai) / 10 * 0.5 pt (inverted — less AI-feel = better)
            persona_score = (
                (2.0 if would_reply else 0.0)
                + (feels_personal / 10.0 * 1.5)
                + (trust / 10.0 * 1.0)
                + ((10.0 - feels_ai) / 10.0 * 0.5)
            )
            scores.append(persona_score)

            deal = judgment.get("deal_breaker") or "—"
            worked = judgment.get("what_worked") or "—"
            details.append(
                f"JUDGE {i+1}: reply={would_reply} personal={feels_personal:.0f}/10 "
                f"trust={trust:.0f}/10 ai-feel={feels_ai:.0f}/10 → {persona_score:.2f}/5"
            )
            details.append(f"  deal_breaker: {deal[:120]}")
            details.append(f"  what_worked: {worked[:120]}")
        except Exception as e:
            details.append(f"JUDGE {i+1} ERROR: {e}")
            scores.append(0.0)

    avg = sum(scores) / len(scores) if scores else 0.0
    return avg, details


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def score_email(
    expected_language: str,
    required_terms: list[str],
    forbidden_greetings: list[str],
    personas: list[str],
) -> None:
    """Score the email in /tmp/eval_results.json and write reward to /logs/verifier/reward.txt."""
    os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)

    if not os.path.exists(EVAL_PATH):
        print(f"No eval results at {EVAL_PATH}, scoring 0")
        with open(REWARD_PATH, "w") as f:
            f.write("0.0")
        return

    try:
        eval_data = json.loads(open(EVAL_PATH).read())
    except Exception as e:
        print(f"Failed to parse eval results: {e}")
        with open(REWARD_PATH, "w") as f:
            f.write("0.0")
        return

    if not eval_data.get("success"):
        error = eval_data.get("error", "unknown")
        print(f"Compose failed: {error}")
        print("HARD FAIL: email not generated")
        with open(REWARD_PATH, "w") as f:
            f.write("0.0")
        return

    email = eval_data.get("email", {})

    print("=" * 70)
    print(f"SUBJECT: {email.get('subject', '')}")
    print("-" * 70)
    print(email.get("body_text", "")[:800])
    print("=" * 70)

    # HARD RULES
    hard_score, hard_details = check_hard_rules(
        email=email,
        expected_language=expected_language,
        required_terms=required_terms,
        forbidden_greetings=forbidden_greetings,
    )
    print("\n--- HARD RULES ---")
    for line in hard_details:
        print(line)
    print(f"HARD SUBTOTAL: {hard_score:.2f}/5")

    # SOFT JUDGE
    soft_score, soft_details = run_persona_judge(
        email=email,
        personas=personas,
        judge_language=expected_language,
    )
    print("\n--- PERSONA JUDGE ---")
    for line in soft_details:
        print(line)
    print(f"SOFT SUBTOTAL: {soft_score:.2f}/5")

    total = hard_score + soft_score
    final = round(total / 10.0, 3)
    print(f"\n{'=' * 70}")
    print(f"TOTAL: {total:.2f}/10 = {final}")
    print("=" * 70)

    with open(REWARD_PATH, "w") as f:
        f.write(str(final))
