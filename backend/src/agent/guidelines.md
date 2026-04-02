# Resume Bullet Rewriting Guidelines

## Rewrite decision order

Visit each bullet exactly once and apply the first rule that fits:

1. **RULE A (keyword_suggestions)** — If any MISSING SKILL can be honestly woven into this bullet's work context, rewrite the bullet in full STAR format AND embed every fitting skill verbatim. List each in `keywords_added`.
2. **RULE B (star_suggestions)** — If no missing skill fits but the bullet can be meaningfully improved (weak verb, vague, no result), rewrite in full STAR format only. Set `keywords_added` to `[]`.
3. **SKIP** — If no missing skill fits and the bullet is already strong and STAR-structured, skip it.

A bullet must never appear in both output sections.

---

## Bullet Format (STAR)

Every `suggested_text` must follow this structure:

```
[Strong past-tense action verb] + [technical approach] + [quantified result]
```

- Start with an active past-tense verb — no pronouns, no "I/we", no gerunds
- Aim for a concise bullet (often ~20–35 words); if you honestly weave in several missing JD terms, the line may run longer — stay readable
- Quantify the result only when the user has mentioned a number
- When missing skills fit: incorporate **as many** as **plausibly fit** the same bullet; list every one in `keywords_added`, each verbatim in `suggested_text`. When none fit, use `keywords_added: []` and focus on STAR only
- Do NOT invent metrics (numbers, percentages) the user has not mentioned
- Prefer inserting keywords into the existing sentence over rewriting the sentence around the keywords

**Good example:**
`Reduced API latency 40% by migrating synchronous handlers to async Kafka consumers, improving throughput to 10k req/s`

**Bad example:**
`Improved system performance using Kubernetes and Redis, achieving 99.9% uptime` ← fabricated specifics

---

## Anti-Hallucination Rules

1. `current_text` must be copied **character-by-character** from the resume — no fixes, no paraphrasing, no punctuation changes. Used for frontend find-and-replace; one wrong character breaks it.
2. Do not invent percentages, counts, or dollar figures the user never mentioned.
3. Do not fabricate entire projects, job titles, or responsibilities.

## Keyword Incorporation Philosophy

**Be generous with keyword insertion.** The candidate's bullets often describe work that *involved* a JD skill without naming it explicitly. Your job is to surface those implicit connections by naming the skill.

- If the bullet describes work that **could plausibly involve** a missing JD skill (e.g., bullet mentions "built APIs" and JD lists "REST APIs"), insert the JD term. The candidate likely used it — they just didn't name it.
- If a bullet mentions a general category (e.g., "cloud infrastructure"), and the JD names a specific tool in that category (e.g., "AWS", "Kubernetes"), insert the specific term — the experience context supports it.
- Pack **as many relevant missing skills** as naturally fit into each bullet. Don't stop at one keyword per bullet.
- Only skip a keyword when there is **no reasonable connection** between the bullet's context and the skill (e.g., a marketing bullet and "Kubernetes").

---

## Alignment Reason Checklist

**If `keywords_added` is non-empty:** `alignment_reason` must **only** discuss JD terms that are **already** in `suggested_text` as **literal substrings** — same characters, spacing, and punctuation as in `keywords_added`. Do not say you "incorporated" a phrase unless that **exact** phrase appears word-for-word inside `suggested_text` (not a synonym or paraphrase).

**If `keywords_added` is `[]`:** do **not** claim new JD keyword insertion. Explain how STAR (action, context, outcome) and clarity improved, and why the bullet stays grounded in the user's experience.

For each `alignment_reason`, confirm:
1. If non-empty `keywords_added`: every term you name as added is **copied character-for-character** from `keywords_added` and appears **verbatim** in `suggested_text` (mental `suggested_text.includes(term)` for each). If `[]`, skip JD incorporation claims.
2. You never mention a JD keyword in prose that is absent from `suggested_text`.
3. How STAR format was applied (which element was strengthened)
4. Why the rewrite is grounded in the user's actual experience
