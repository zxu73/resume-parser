# Resume Bullet Rewriting Guidelines

## Rewrite decision order

For each weak bullet:

1. **Missing skills first** — If any MISSING SKILL can be honestly woven into that experience, incorporate it. Use the **exact** JD string in `suggested_text` and list every one you add in `keywords_added` (each must appear verbatim in the bullet).
2. **STAR if no fit** — If no missing skill fits without stretching the truth, do **not** force keywords. Set `keywords_added` to `[]` and improve the bullet with stronger STAR structure, clarity, and grounded impact.

---

## Minimal-Edit Principle (CRITICAL)

`suggested_text` must be the original `current_text` with **small insertions or appended phrases** — NOT a rewrite.

**Allowed changes:**
- Insert a keyword phrase using "using [keyword]", "via [keyword]", "leveraging [keyword]", or "with [keyword]"
- Append a short clause like ", improving [result]" or ", utilizing [keyword]"
- Swap one or two words to fit a keyword naturally

**NOT allowed:**
- Rearranging the sentence order
- Replacing the original action verb with a different one
- Rewriting the bullet from scratch with different wording
- Changing the subject, object, or structure of the sentence

**Test:** At least 70% of the words in `current_text` should appear in `suggested_text` in the same order. If you find yourself writing a completely new sentence, stop — go back to the original and just insert the keywords.

**Example:**
- current_text: `Implemented upload, persistence, and retrieval workflows that turned complex healthcare claims into a searchable internal application.`
- GOOD suggested_text: `Implemented upload, persistence, and retrieval workflows using REST APIs and cloud-native engineering that turned complex healthcare claims into a searchable internal application.`
- BAD suggested_text: `Designed and implemented a searchable internal application for healthcare claims by developing upload, persistence, and retrieval workflows, enabling 200+ users to access claims data efficiently.`

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
