# Resume Bullet Rewriting Guidelines

## Bullet Format (STAR)

Every `suggested_text` must follow this structure:

```
[Strong past-tense action verb] + [technical approach] + [quantified result]
```

- Start with an active past-tense verb — no pronouns, no "I/we", no gerunds
- Aim for a concise bullet (often ~20–35 words); if you honestly weave in several missing JD terms, the line may run longer — stay readable
- Quantify the result only when the user has mentioned a number
- Incorporate **as many** missing JD skills as **plausibly fit** the same bullet (no fixed cap); list every one you add in `keywords_added`, each verbatim in `suggested_text`
- Do NOT add skills, tools, or metrics the user has not mentioned

**Good example:**
`Reduced API latency 40% by migrating synchronous handlers to async Kafka consumers, improving throughput to 10k req/s`

**Bad example:**
`Improved system performance using Kubernetes and Redis, achieving 99.9% uptime` ← fabricated specifics

---

## Anti-Hallucination Rules (Absolute)

1. `current_text` must be copied **character-by-character** from the resume — no fixes, no paraphrasing, no punctuation changes. Used for frontend find-and-replace; one wrong character breaks it.
2. `suggested_text` must be grounded in what the user actually described — expand and sharpen, never fabricate.
3. Do not add skills, frameworks, or tools the user has not demonstrated.
4. Do not invent percentages, counts, or dollar figures.
5. If a missing skill does not fit the experience context, omit it rather than force it in.

---

## Alignment Reason Checklist

For each `alignment_reason`, confirm all three:
1. Which missing JD skills were added (and why they fit)
2. How STAR format was applied (which element was strengthened)
3. Why the rewrite is grounded in the user's actual experience
