# program-writer

Autonomous prompt engineering for the RobotSpeed section-writer. You are a
professional prompt engineer and a meta-agent that improves the system prompt
used by `writeSection()` in the RobotSpeed repo.

Your job is NOT to rewrite sections yourself. Your job is to improve the
prompt in **one file** so that the next run of the eval harness produces a
higher composite score on the fixtures in `tasks-writer/`.

## Directive

**Make RobotSpeed articles feel like journalism, not AI content.** The product
owner's words, verbatim:

> "Le but c'est d'écrire des articles toujours mieux, unique, meilleure en
> seo, meilleure data, meilleure contenu, meilleure à bypass winston AI
> checker et autres ai checker, etc... Vraiment du travail journalistique."

The composite score encodes this goal across 5 dimensions (multiplicative
mean with a 40-point floor penalty):

- **winston**     — humanness bypass (currently mocked at 80 — not yet the signal)
- **factuality**  — fraction of claims supported by injected research facts
- **originality** — 1 − mean cosine similarity vs the top-10 SERP embeddings
- **seo**         — keyword placement, headings, anti-fluff
- **specificity** — density of numbers, dates, proper nouns, citations

A full description lives in `libs/content-system-v2/pipeline/eval/score.ts`.
Read it before proposing changes to understand the reward shape.

## 🔒 Single edit target

You may ONLY modify this file in the RobotSpeed repo:

    libs/content-system-v2/pipeline/section-writer-prompts.ts

All other files are **frozen**. Specifically, you must NOT modify:

- `libs/content-system-v2/pipeline/section-writer.ts` (the 3591-line
  orchestration file — it imports from section-writer-prompts.ts and
  wraps the prompt with per-section context)
- `libs/content-system-v2/pipeline/eval/judge.ts` (the scoring rubric —
  SHA256 pinned below)
- `libs/content-system-v2/pipeline/eval/score.ts` (the composite formula)
- `libs/content-system-v2/pipeline/eval/originality.ts`
- `libs/content-system-v2/pipeline/research.ts` and research-facts.ts
- `scripts/section-writer-eval.ts` and `scripts/validate-prompts.ts`
- Any other file outside `section-writer-prompts.ts`

## 🔒 Hard guardrails (enforced by validate-prompts.ts)

Before every iteration, `scripts/validate-prompts.ts` runs automatically via
`agent_writer.py`. If any of these fail, the iteration is aborted and the
previous version of `section-writer-prompts.ts` is kept:

1. **Export signature**: `buildSectionWriterSystemPrompt(language: string): string`
   must still exist as a function with arity 1.

2. **Minimum length**: output ≥ 5000 chars for each of `en`, `fr`, `de`.
   A prompt shorter than that almost certainly means you deleted a safety
   rule. Don't.

3. **Critical markers** (MUST appear in every language output):
   `WINSTON AI`, `NEVER INVENT`, `Case studies`, `Statistics`,
   `OUTPUT FORMAT`, `<h2>`, `NO markdown`.
   These gate against:
   - removing Winston AI humanness guidance → detectable AI spam
   - removing anti-hallucination → legal liability from invented statistics
   - removing output format → broken parser downstream

4. **Link-seller guard**: `section-writer.ts` still contains the
   `externalLinksEnabled !== false ?` ternary. This gates the Wikipedia/
   authority external links block for customers who sell backlinks as a
   business — their paid placements must not be polluted by free parasitic
   links. HARD RED LINE, tied to revenue.

5. **Required exports on section-writer.ts**: `writeSection`, `writeIntro`,
   `writeConclusion`, `writeFAQ` must still exist as async functions (even
   though you're not allowed to edit that file, you must not break its
   compilation indirectly).

6. **Judge SHA256 pin** (prevents self-inflation):
   ```
   eval/judge.ts SHA256 = 3f90c8cf7ae408b7aa31c84d9059764cf77ac62e3de2150cbb3178594c9b714a
   ```
   Any tampering with the scoring rubric causes an immediate abort.

## What the current prompt looks like

Read `libs/content-system-v2/pipeline/section-writer-prompts.ts` first. It's
a single function that returns a ~7000-char template literal. The structure:

1. Opening role ("You are an expert ${langName} SEO copywriter")
2. Winston AI bypass section (burstiness, vocabulary, structure, imperfections, perplexity)
3. Grammar protection (interpolated per language)
4. Writing rules
5. Visual structure (lists, tables)
6. When to use tables
7. Banned words per language
8. Anti-patterns
9. Forbidden hallucinations (the NEVER INVENT block — see guardrail #3)
10. USE INSTEAD block
11. E-E-A-T signals
12. Human writing style
13. H3 placement rule
14. Output format

The whole prompt is a single template literal. You can rewrite any portion
freely **as long as the guardrails above hold**.

## First-iteration priorities (from real baseline measurement)

Baseline measured April 8 2026 on the Swiss labor-law fixture (Bedrock
Sonnet 4.5 writing against 10 clean research facts):

| dimension   | score | status             |
|-------------|-------|--------------------|
| factuality  | 19    | critically low ⚠  |
| originality | 33    | below floor ⚠     |
| seo         | 88    | already strong    |
| specificity | 69    | ok                |

Raw geometric mean: **49.63/100**. Composite after floor penalty: **24.81**.

Your first iterations should focus on:

### Priority 1 — Originality (currently 33, target ≥ 50)

The writer produces content ~70% similar to the top-10 SERP results for
the keyword. The current prompt has NO guidance on differentiation. Possible
directions:

- Add an explicit "write the angle these sources miss" instruction.
- Encourage contrarian framing when supported by the research facts.
- Penalize restating common knowledge — reward specific detail.
- Banish generic opening hooks that every article uses.

**Note**: the fixture already contains `originality_data.serp_titles` and
`originality_data.serp_urls` — these are NOT currently injected into the
prompt, but the harness code in `section-writer.ts` builds the user prompt
per-call and you don't control that. If you want SERP-aware differentiation,
you have to describe it abstractly ("the writer should assume competitors
cover X, Y, Z — find a gap"). Future phases may wire SERP URL injection
directly; for now, work with the abstraction.

### Priority 2 — Factuality (currently 19, target ≥ 60)

Counter-intuitively, the writer given 15 clean facts produces FEWER
grounded claims (3/16) than the published article had with 2 truncated
facts (8/15). This suggests the current prompt doesn't push the writer to
anchor its claims to the injected research. Possible directions:

- Explicit instruction to cite the research array inline ("According to
  the RESEARCH section...")
- Forbid claims that don't trace to the research or to basic domain
  knowledge
- Reward paraphrase-with-attribution over free-form narration

### Priority 3 — Don't regress SEO or specificity

- Keep SEO ≥ 85 (currently 88)
- Keep specificity ≥ 65 (currently 69)
- Any iteration that raises originality/factuality but tanks these is a
  regression — the composite is multiplicative, so sacrificing any dim
  kills the score.

## The eval loop

Each Harbor run of `tasks-writer/swiss-labor-law`:

1. `agent_writer.py` runs `scripts/validate-prompts.ts` (fast, no cost)
2. If guards pass, runs `scripts/section-writer-eval.ts <fixture_id> --json`
3. That script calls `writeSection()` on Bedrock Sonnet 4.5 (~$0.025)
4. Then runs 3 Gemini Flash judges + 1 OpenAI embedding (~$0.0006 total)
5. Writes per-fixture JSON report + returns composite to the verifier
6. Verifier writes reward = composite / 100 to `/logs/verifier/reward.txt`

**Per-iteration cost**: ~$0.03. Overnight cap (20 iterations × 1 fixture ×
3 runs each) is ~$2 — well under any reasonable hard cap.

## What to read before the first iteration

Authoritative context lives in the RobotSpeed repo:

- `libs/content-system-v2/pipeline/eval/FINDINGS.md` — 8 findings from
  the harness build, including the two prod bugs already fixed (keyFacts
  parser +15 specificity points, and the Wikipedia-only external links
  issue which is NOT in your edit scope but is context for why the
  baseline is what it is)
- `libs/content-system-v2/pipeline/eval/RESUME.md` — pickup doc, baseline
  numbers, targets
- `libs/content-system-v2/pipeline/section-writer-prompts.ts` — the file
  you will edit

## What you should NOT do

- Don't shorten the prompt hoping it'll be "tighter". 5000 chars is the
  floor. The safety rules are long for a reason — every one of them
  exists because a past generation produced something bad.
- Don't remove the Winston AI bypass section. The user's #1 goal is
  passing AI detection, and the `winston` dimension will be unmocked
  in Phase 3.
- Don't remove the NEVER INVENT block. Invented statistics have caused
  real legal issues for clients.
- Don't modify the output format rules. Downstream parsers expect the
  exact HTML shape described.
- Don't try to be clever about the grammar protection interpolation —
  `getGrammarProtectionRules()` is called for its side effect of
  injecting language-specific rules, and removing that interpolation
  silently degrades non-English output.
