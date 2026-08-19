import difflib
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional, TypedDict
from pydantic import BaseModel, Field, field_validator, model_validator
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END

_BULLET_GUIDELINES = (Path(__file__).parent / "guidelines.md").read_text(encoding="utf-8")



@lru_cache(maxsize=4)
def _llm_for(model: str) -> ChatOpenAI:
    # Cached so the underlying httpx client / connection pool is reused across
    # requests instead of being rebuilt on every node invocation.
    return ChatOpenAI(model=model)


def _llm() -> ChatOpenAI:
    # Read the env var each call (so REASONING_MODEL stays runtime-configurable)
    # but reuse the client per distinct model name.
    return _llm_for(os.getenv("REASONING_MODEL", "gpt-4o-mini"))


# ── Evaluation Agent schema ──────────────────────────────────────────────

class ClarifyingQuestion(BaseModel):
    id: str = Field(..., description="Stable identifier (snake_case), e.g. 'docker_prod_use'")
    question: str = Field(..., description="The question to show the user, answerable in <15 seconds")
    skill_targeted: str = Field(..., description="Which missing skill or vague experience this question clarifies")
    target_bullet: str = Field(
        default="",
        description=(
            "The ONE resume bullet this question is about, copied CHARACTER-FOR-CHARACTER from the "
            "resume (including any leading bullet symbol). If the user confirms, this exact bullet "
            "is the one that gets rewritten."
        ),
    )
    target_experience: str = Field(
        default="",
        description="The role/company heading that bullet sits under, e.g. 'Software Engineer | ABC Company'",
    )
    question_type: str = Field(..., pattern="^(multiple_choice|free_text)$")
    choices: List[str] = Field(
        default_factory=list,
        description="For multiple_choice: 3-4 concrete options. For free_text: must be [].",
    )


class EvaluationResponse(BaseModel):
    executive_summary: str
    overall_score: float = Field(..., ge=1, le=10)
    job_match_percentage: float = Field(..., ge=0, le=100)
    strengths: List[str]
    weaknesses: List[str]
    missing_skills: List[str]
    matching_skills: List[str]
    clarifying_questions: List[ClarifyingQuestion] = Field(
        default_factory=list,
        max_length=5,
        description="3-5 questions to ask the user before generating rewrites",
    )


# ── Rating Agent schema ──────────────────────────────────────────────────

class DetailedRating(BaseModel):
    score: float = Field(..., ge=1, le=10)
    justification: str


class DetailedRatings(BaseModel):
    content_quality: DetailedRating
    skills_match: DetailedRating
    experience_relevance: DetailedRating


class ParaphrasingSuggestion(BaseModel):
    current_text: str = Field(..., description="Current text from the resume")
    suggested_text: str = Field(
        ...,
        description=(
            "Improved bullet in STAR format. If keywords_added is non-empty, every entry must appear as a "
            "literal substring (exact spelling). If keywords_added is empty, STAR/impact improvement only — no forced JD terms"
        ),
    )
    keywords_added: List[str] = Field(
        ...,
        min_length=0,
        description=(
            "JD terms from MISSING SKILLS embedded in suggested_text (exact copy, each a literal substring). "
            "Use [] when no missing skill fits — STAR-only rewrite"
        ),
    )
    job_requirement_reference: str = Field(..., description="Specific job requirement this addresses")
    alignment_reason: str = Field(
        ...,
        description=(
            "Why this rewrite helps. If keywords_added is non-empty: any JD term you mention as incorporated "
            "MUST appear word-for-word in suggested_text and match keywords_added (no synonyms). "
            "If keywords_added is empty: explain STAR/impact improvements only — do not claim new JD keywords"
        ),
    )

    @field_validator("alignment_reason")
    @classmethod
    def tidy_alignment_reason(cls, v: str) -> str:
        # Cosmetic normalization of model prose: collapse doubled commas and
        # "and and", squeeze runs of whitespace, trim stray leading/trailing
        # commas and space.
        v = re.sub(r"\s*,\s*,", ",", v)
        v = re.sub(r"\s*and\s*and\s*", " and ", v)
        v = re.sub(r"\s{2,}", " ", v).strip()
        return re.sub(r"^[,\s]+|[,\s]+$", "", v)

    @model_validator(mode="after")
    def strip_missing_keywords(self) -> "ParaphrasingSuggestion":
        # LLMs sometimes claim keywords that aren't actually in suggested_text.
        # Silently drop those instead of raising — RatingResponse.normalize_sections
        # then moves any entry left with no keywords into star_suggestions.
        #
        # Before dropping, recover the common near-miss: the model wrote the keyword
        # with different capitalisation ("docker containerization"). ATS matching is
        # literal, so rather than lose a keyword the user may have confirmed, rewrite
        # that span of suggested_text to the exact casing we were given. No LLM call.
        kept: List[str] = []
        for kw in self.keywords_added:
            if kw in self.suggested_text:
                kept.append(kw)
                continue
            at = self.suggested_text.lower().find(kw.lower())
            if at != -1:
                self.suggested_text = (
                    self.suggested_text[:at] + kw + self.suggested_text[at + len(kw):]
                )
                kept.append(kw)
        self.keywords_added = kept
        return self


class PriorityRecommendation(BaseModel):
    priority: str = Field(..., pattern="^(High|Medium|Low)$")
    title: str
    description: str
    specific_example: str
    paraphrasing_suggestion: "ParaphrasingSuggestion"


class RatingResponse(BaseModel):
    detailed_ratings: DetailedRatings
    keyword_suggestions: List[PriorityRecommendation] = Field(
        ...,
        min_length=0,
        max_length=15,
        description="Suggestions that insert missing JD skills. Each must have non-empty keywords_added.",
    )
    star_suggestions: List[PriorityRecommendation] = Field(
        ...,
        min_length=0,
        max_length=10,
        description="STAR-format improvements only. Each must have keywords_added: [].",
    )

    @model_validator(mode="after")
    def normalize_sections(self) -> "RatingResponse":
        # Auto-migrate keyword_suggestions with empty keywords_added → star_suggestions.
        # (ParaphrasingSuggestion may have stripped invalid keywords, leaving the list empty.)
        kept_keyword = []
        migrated_to_star = []
        for rec in self.keyword_suggestions:
            if rec.paraphrasing_suggestion.keywords_added:
                kept_keyword.append(rec)
            else:
                migrated_to_star.append(rec)
        self.keyword_suggestions = kept_keyword

        # Clear stray keywords_added on star_suggestions (STAR-only section).
        for rec in self.star_suggestions:
            rec.paraphrasing_suggestion.keywords_added = []

        # Drop star_suggestions whose bullet is already covered by keyword_suggestions.
        keyword_texts = {
            rec.paraphrasing_suggestion.current_text.strip()
            for rec in self.keyword_suggestions
        }
        combined_star = list(self.star_suggestions) + migrated_to_star
        seen: set[str] = set()
        deduped_star = []
        for rec in combined_star:
            bullet = rec.paraphrasing_suggestion.current_text.strip()
            if bullet in keyword_texts or bullet in seen:
                continue
            seen.add(bullet)
            deduped_star.append(rec)
        self.star_suggestions = deduped_star
        return self


# ── Experience Optimizer schema ──────────────────────────────────────────

class ExperienceComparison(BaseModel):
    resume_experience_index: int = Field(..., description="Index of experience in original resume")
    resume_experience_title: str
    should_replace: bool = Field(..., description="True if pool experience is better")
    pool_experience_index: Optional[int] = Field(None, description="Index of pool experience to use if replacing")
    replacement_reason: str = Field(..., description="Why this replacement improves job alignment")
    relevance_score_resume: float = Field(..., ge=0, le=100)
    relevance_score_pool: float = Field(..., ge=0, le=100)


class SmartExperienceOptimization(BaseModel):
    comparisons: List[ExperienceComparison]
    swaps_made: int
    optimization_summary: str


# ── Instructions ─────────────────────────────────────────────────────────

EVALUATION_INSTRUCTION = (
    "You are a resume evaluation specialist. Your output feeds directly into a rewriting agent,\n"
    "so accuracy and completeness of missing_skills is critical.\n"
    "Respond with structured JSON matching the schema. No markdown, no explanations.\n\n"

    "=== FIELDS ===\n"
    "1. executive_summary — 2-3 sentences on overall quality and job fit.\n"
    "2. overall_score — 1-10 based on quality and job alignment.\n"
    "3. job_match_percentage — 0-100 based on skill overlap.\n"
    "4. strengths — 3-5 specific strengths.\n"
    "5. weaknesses — 3-5 areas needing improvement.\n"
    "6. missing_skills — EXHAUSTIVE list of every keyword, skill, tool, framework, and methodology\n"
    "   mentioned in the JD but absent from the resume. Use the EXACT wording from the JD.\n"
    "   This list drives ATS keyword insertion downstream — do NOT omit minor skills.\n"
    "7. matching_skills — skills present in both resume and JD.\n"
    "8. clarifying_questions — 3-5 targeted questions to ask the user before rewriting bullets.\n\n"

    "=== GUIDELINES ===\n"
    "- Do NOT recommend adding a Professional Summary.\n"
    "- For missing_skills, go beyond obvious ones — include specific tools, certifications,\n"
    "  methodologies, and soft skills mentioned in the JD.\n\n"

    "=== CLARIFYING QUESTIONS ===\n"
    "Generate 3-5 questions. EVERY question must be anchored to ONE specific bullet already in the\n"
    "resume, and must ask whether the candidate used a specific MISSING SKILL while doing THAT work.\n"
    "If the user confirms, that exact bullet gets rewritten to name the skill — so the anchor decides\n"
    "which line changes. A question with no bullet anchor is useless downstream.\n\n"

    "Rules for each question:\n"
    "- id: short snake_case identifier (e.g. 'docker_billing_svc'). Unique across the list.\n"
    "- skill_targeted: the exact missing skill string this question probes (copy it verbatim from missing_skills).\n"
    "- target_bullet: the ONE resume bullet the question is about, copied CHARACTER-FOR-CHARACTER from the\n"
    "  resume, including any leading bullet symbol. It MUST appear in the resume exactly as you write it.\n"
    "  Never paraphrase, re-punctuate, or trim it.\n"
    "- target_experience: the role/company heading that bullet sits under.\n"
    "- question: ONE sentence that names the concrete work from target_bullet and asks whether the\n"
    "  skill was used in it. Pattern: 'When you <the work in that bullet>, did you use <skill> to <plausible purpose>?'\n"
    "- question_type: 'multiple_choice' when the answer falls in a small set, otherwise 'free_text'.\n"
    "- choices: for multiple_choice, 3-4 concrete mutually exclusive options. Always include a clear\n"
    "  negative option (e.g. 'No, not on this work'). For free_text, choices MUST be [].\n"
    "- Spread questions across DIFFERENT bullets — never anchor two questions to the same bullet.\n"
    "- Prefer bullets that are vague or under-specified; those gain the most from a rewrite.\n\n"

    "Good examples (anchored to real work):\n"
    "- target_bullet: '• Worked with databases and APIs for internal reporting tools'\n"
    "  Q: 'When you built those internal reporting tools, did you use PostgreSQL performance tuning\n"
    "     to speed up the queries?' type: multiple_choice,\n"
    "  choices: ['Yes, I tuned queries/indexes', 'Yes, but someone else did the tuning', 'No, not on this work']\n"
    "- target_bullet: '• Collaborated with team members on projects and code reviews'\n"
    "  Q: 'On that team, did you mentor or lead any of the engineers whose code you reviewed?'\n"
    "     type: multiple_choice, choices: ['Yes, I formally mentored 1-2', 'Yes, informally', 'No, peer reviews only']\n\n"

    "Bad examples (avoid these):\n"
    "- Unanchored: 'Have you used Docker in production?' (no bullet — the rewriter won't know what to change)\n"
    "- Vague: 'Tell me about your experience.' (not answerable in 15s)\n"
    "- Leading: 'You have Kubernetes experience, right?' (assumes the answer)\n"
    "- Redundant: asking about a skill that's already in matching_skills.\n"
    "- Paraphrased anchor: target_bullet that does not appear verbatim in the resume.\n\n"

    "OUTPUT FORMAT: Return ONLY valid JSON matching the schema."
)

RATING_INSTRUCTION = (
    "You are an expert resume content specialist and ATS optimization strategist.\n"
    "For every bullet you rewrite, produce a full STAR-format sentence:\n"
    "  [Strong past-tense verb] + [technical approach / context] + [result or impact]\n"
    "Do NOT invent metrics, percentages, or project names the user never mentioned.\n"
    "When you add keywords, use EXACT JD wording — synonyms do NOT count for ATS.\n\n"

    + _BULLET_GUIDELINES +

    "\n\n=== SECTION 1: DETAILED RATINGS (scores 1-10) ===\n"
    "- content_quality: clarity, impact, professionalism\n"
    "- skills_match: keyword overlap between resume and JD\n"
    "- experience_relevance: alignment with JD requirements\n\n"

    "=== SECTION 2: CONFIRMED SKILLS (highest priority) ===\n"
    "You may be given a CONFIRMED block: bullets the user has told us they actually did the work in,\n"
    "paired with the missing skills they confirmed using there, in their own words. This is ground\n"
    "truth, not a guess — the user answered a question specifically so the skill would show up.\n\n"
    "For each bullet in that block you MUST emit exactly ONE keyword_suggestions entry that rewrites\n"
    "it and embeds EVERY skill confirmed for it, verbatim. Several skills on one bullet is expected —\n"
    "put them all in that single rewrite rather than splitting or dropping any. Ground the wording in\n"
    "what the user said (their tools, scale, role); never contradict them and never invent numbers.\n"
    "Silently omitting a confirmed skill is the worst outcome here: the user answered for nothing.\n\n"

    "EMBEDDING AWKWARD PHRASES: some JD skills are noun phrases that do not drop naturally into a\n"
    "sentence. Embed them ANYWAY, verbatim, with a carrier clause. Never reword them to read better —\n"
    "a rephrased keyword scores zero with an ATS, so a slightly formal clause beats a natural miss.\n"
    "  'Team leadership and mentoring'       -> '... while providing Team leadership and mentoring to two juniors'\n"
    "  'CI/CD pipelines with GitHub Actions' -> '... by building CI/CD pipelines with GitHub Actions'\n"
    "  'PostgreSQL performance tuning'       -> '... applying PostgreSQL performance tuning to cut query time'\n"
    "  'AWS (EC2, S3, Lambda)'               -> '... deployed on AWS (EC2, S3, Lambda)'\n"
    "Keep the exact capitalisation, punctuation and word order given, even mid-sentence.\n\n"

    "=== SECTION 3: REMAINING BULLETS ===\n"
    "After handling the CONFIRMED block, walk every other bullet in the resume once, in order, and\n"
    "apply exactly ONE rule per bullet — never both, never the same bullet in both output lists.\n\n"

    "RULE A -> keyword_suggestions:\n"
    "  Condition: at least one still-unplaced MISSING SKILL can be honestly woven into this bullet.\n"
    "  Be GENEROUS — if the bullet describes work that could plausibly involve a JD skill, insert it.\n"
    "  The candidate likely used it but did not name it. Aim for 6-10 entries in this section when\n"
    "  the resume supports them, but never fabricate whole projects or responsibilities.\n"
    "  Action: rewrite in full STAR format with every fitting skill embedded verbatim.\n"
    "  keywords_added must be non-empty.\n\n"

    "RULE B -> star_suggestions (target 5-10 items):\n"
    "  Condition: no missing skill plausibly fits AND the bullet can be meaningfully improved\n"
    "  (vague, weak verb, lacks a result, no STAR structure).\n"
    "  Action: rewrite in full STAR format only. keywords_added MUST be [].\n"
    "  Do NOT apply if the bullet is already clear and well-structured.\n\n"

    "SKIP: no missing skill fits AND the bullet is already strong -> do not emit it.\n\n"

    "NO DUPLICATES: each bullet's current_text appears in at most one entry across both lists.\n"
    "KEYWORD COVERAGE: after the pass, place any still-unplaced missing skill on the best Rule-A\n"
    "bullet that can carry it. Each missing skill should appear in AT MOST 2 entries.\n\n"

    "=== ATS KEYWORD RULES (verify before you output JSON) ===\n"
    "- Pick keywords ONLY from the MISSING SKILLS / CONFIRMED lists. Copy each CHARACTER-FOR-CHARACTER.\n"
    "- suggested_text MUST contain every entry of keywords_added as a LITERAL SUBSTRING.\n"
    "  A keyword that is not literally present is discarded downstream — check each one.\n"
    "- Use EXACT wording, not synonyms.\n"
    "  Bad: list \"Kubernetes\" but write only \"container orchestration\".\n"
    "  Good: write \"... deployed services on Kubernetes ...\" and list \"Kubernetes\".\n"
    "- alignment_reason must name every keyword in keywords_added and claim nothing beyond them.\n"
    "- If keywords_added is [], alignment_reason describes STAR/impact only — no JD keyword claims.\n\n"

    "OTHER RULES:\n"
    "1. Every suggestion MUST include a paraphrasing_suggestion. Never omit it.\n"
    "2. NEVER invent entire projects or job responsibilities. But DO name JD skills when the\n"
    "   bullet's context plausibly involves them.\n"
    "3. For each: priority | title (exact job title from resume) | description | specific_example\n"
    "4. current_text — copy the bullet character-for-character, including any bullet symbol.\n"
    "   The document editor finds the paragraph by exact text match; any deviation breaks it silently.\n\n"

    "Do NOT recommend adding a professional summary.\n\n"

    "OUTPUT FORMAT: Return ONLY valid JSON matching RatingResponse schema.\n"
    "The JSON must have keys: detailed_ratings, keyword_suggestions, star_suggestions."
)


OPTIMIZER_INSTRUCTION = (
    "You are an expert at optimizing resumes by replacing experiences to improve job alignment.\n\n"

    "=== TASK ===\n"
    "Find optimal 1-for-1 swaps between resume experiences and pool experiences.\n\n"

    "=== TWO CRITERIA FOR A BETTER SWAP ===\n"
    "1. JD fit and keywords — The pool experience should match the job more closely: more exact or\n"
    "   paraphrased overlap with JD keywords (tools, domains, responsibilities), and clearer alignment\n"
    "   with what the role actually requires (title, industry, scope).\n"
    "2. Stronger descriptions — The pool experience's bullet text should better demonstrate the\n"
    "   candidate's skills: clearer STAR structure, quantified results, concrete actions, and\n"
    "   evidence of impact versus vague or generic wording on the resume.\n\n"
    "When comparing resume vs pool for the same role, weight BOTH criteria. A swap is compelling only\n"
    "when the pool entry wins meaningfully on JD alignment and/or demonstrably stronger bullets.\n\n"

    "=== SCORING (0-100 per experience) ===\n"
    "Combine into one score: (a) JD keyword overlap + role/domain fit, and (b) strength of written\n"
    "descriptions for showcasing skills and impact. Do not reward keyword stuffing without substance.\n\n"

    "=== PROCESS ===\n"
    "1. Score ALL resume experiences using the two criteria above.\n"
    "2. Score ALL pool experiences the same way.\n"
    "3. For each resume experience, find the highest-scoring pool candidate.\n"
    "4. Recommend replacement ONLY if pool score exceeds resume score by 20+ points.\n"
    "5. Each pool experience replaces at most ONE resume experience.\n"
    "6. Ties: choose the candidate with the larger score difference.\n"
    "7. Never add or remove experiences — swap 1-for-1 only.\n\n"

    "=== OUTPUT (per resume experience) ===\n"
    "resume_experience_index (0-based) | resume_experience_title (exact) | should_replace\n"
    "pool_experience_index (null if no swap) | relevance_score_resume | relevance_score_pool\n"
    "replacement_reason — cite JD keywords/fit AND/OR how pool bullets better show skills vs resume.\n\n"

    "Be conservative. Only swap when the improvement is clear and meaningful.\n\n"

    "OUTPUT FORMAT: Return ONLY valid JSON matching the schema. No markdown, no explanations."
)


# ── State types ──────────────────────────────────────────────────────────

class ResumeState(TypedDict):
    resume_text: str
    job_description: str
    evaluation: Optional[EvaluationResponse]
    missing_skills: list
    strengths: list
    weaknesses: list
    # [{"question", "answer", "skill_targeted", "target_bullet"}] — the last two are
    # optional; answers without them are passed as plain context.
    answers: list
    rating: Optional[RatingResponse]


class OptimizerState(TypedDict):
    resume_text: str
    job_description: str
    pool_experiences: str
    optimization: Optional[SmartExperienceOptimization]


# ── Node functions ───────────────────────────────────────────────────────

def _snap_to_resume(bullet: str, resume: str) -> str:
    """Force target_bullet to be verbatim resume text, or drop the anchor.

    A near-miss anchor is worse than none: the rewrite would carry a current_text the
    document editor can never match. Snap to the closest real line when the model
    paraphrased lightly, otherwise return "" and let the sweep handle that skill.
    """
    bullet = (bullet or "").strip()
    if not bullet:
        return ""
    if bullet in resume:
        return bullet
    lines = [ln.strip() for ln in resume.splitlines() if ln.strip()]
    match = difflib.get_close_matches(bullet, lines, n=1, cutoff=0.75)
    return match[0] if match and match[0] in resume else ""


async def evaluate_node(state: ResumeState) -> dict:
    result = await _llm().with_structured_output(EvaluationResponse).ainvoke([
        SystemMessage(content=EVALUATION_INSTRUCTION),
        HumanMessage(content=f"RESUME:\n{state['resume_text']}\n\nJOB DESCRIPTION:\n{state['job_description']}"),
    ])
    for q in result.clarifying_questions:
        q.target_bullet = _snap_to_resume(q.target_bullet, state["resume_text"])
    return {
        "evaluation": result,
        "missing_skills": result.missing_skills,
        "strengths": result.strengths,
        "weaknesses": result.weaknesses,
    }


def _lines_block(items: List[str]) -> str:
    return "\n".join(f"  - {i}" for i in items) or "  (none)"


_DENIAL_PATTERNS = re.compile(
    r"^(no|none|nope|never|n/?a|not really|no experience|no,)",
    re.IGNORECASE,
)


def _is_denial(answer: str) -> bool:
    return bool(_DENIAL_PATTERNS.match(answer.strip()))


def _confirmed_block(answers: list, resume: str) -> tuple:
    """Group confirmed answers by the bullet they were anchored to.

    Grouping by bullet (not by skill) is what lets one rewrite carry several
    confirmed skills — the prompt then asks for exactly one entry per bullet, so
    two skills on the same line can never produce two competing rewrites of it.
    Returns (prompt_block, confirmed_skills).
    """
    grouped: dict = {}
    confirmed: List[str] = []
    for a in answers or []:
        answer = (a.get("answer") or "").strip()
        skill = (a.get("skill_targeted") or "").strip()
        bullet = a.get("target_bullet") or ""
        if not answer or _is_denial(answer) or not skill:
            continue
        # Only trust an anchor we can find verbatim; otherwise the rewrite would
        # carry a current_text the document editor can never match.
        if not bullet or bullet not in resume:
            continue
        grouped.setdefault(bullet, []).append({"skill": skill, "answer": answer})
        if skill not in confirmed:
            confirmed.append(skill)

    if not grouped:
        return "", confirmed

    chunks = []
    for bullet, items in grouped.items():
        skills = "\n".join(f"    * {i['skill']}" for i in items)
        said = "\n".join(f"    - \"{i['answer']}\"" for i in items)
        chunks.append(
            f"  BULLET (copy verbatim into current_text):\n    {bullet}\n"
            f"  MUST embed these confirmed skills, verbatim, in ONE rewrite of that bullet:\n{skills}\n"
            f"  What the user told us:\n{said}"
        )
    return "\n\n".join(chunks), confirmed


async def rate_node(state: ResumeState) -> dict:
    resume = state["resume_text"]
    answers = state.get("answers") or []
    confirmed_block, confirmed = _confirmed_block(answers, resume)

    # Skills the user confirmed are handled by the CONFIRMED block; the rest are
    # the free-roaming pool for the per-bullet pass.
    remaining = [s for s in (state.get("missing_skills") or []) if s not in confirmed]

    sections = [
        f"JOB DESCRIPTION:\n{state['job_description']}",
        f"RESUME:\n{resume}",
    ]
    if confirmed_block:
        sections.append(
            "CONFIRMED — the user answered a question for each of these and said yes.\n"
            "Emit exactly ONE keyword_suggestions entry per bullet below, embedding every\n"
            "skill listed under it verbatim:\n\n" + confirmed_block
        )
    sections.append(f"REMAINING MISSING SKILLS (place these across the other bullets):\n{_lines_block(remaining)}")
    sections.append(
        "RESUME STRENGTHS (already good — don't rewrite unless they can carry a missing skill):\n"
        + _lines_block(list(state.get("strengths") or []))
    )
    sections.append(
        "RESUME WEAKNESSES (priority targets for STAR rewrites):\n"
        + _lines_block(list(state.get("weaknesses") or []))
    )

    unanchored = [
        a for a in answers
        if (a.get("answer") or "").strip()
        and not _is_denial((a.get("answer") or ""))
        and not (a.get("target_bullet") and a["target_bullet"] in resume)
    ]
    if unanchored:
        qa = "\n\n".join(f"Q: {a.get('question','')}\nA: {a.get('answer','')}" for a in unanchored)
        sections.append(
            "ADDITIONAL USER CONTEXT (no specific bullet attached — treat as ground truth, use it to\n"
            "justify keyword insertions, never contradict it):\n" + qa
        )

    result = await _llm().with_structured_output(RatingResponse).ainvoke([
        SystemMessage(content=RATING_INSTRUCTION),
        HumanMessage(content="\n\n".join(sections)),
    ])
    return {"rating": result}


async def optimize_node(state: OptimizerState) -> dict:
    result = await _llm().with_structured_output(SmartExperienceOptimization).ainvoke([
        SystemMessage(content=OPTIMIZER_INSTRUCTION),
        HumanMessage(content=f"RESUME:\n{state['resume_text']}\n\nJOB DESCRIPTION:\n{state['job_description']}\n\nPOOL:\n{state['pool_experiences']}"),
    ])
    return {"optimization": result}


# ── Compiled graphs ──────────────────────────────────────────────────────

# Evaluation only — runs before the clarifying-questions step.
_eg = StateGraph(ResumeState)
_eg.add_node("evaluate", evaluate_node)
_eg.add_edge(START, "evaluate")
_eg.add_edge("evaluate", END)
evaluate_only_graph = _eg.compile()

# Rating — runs after the user answers clarifying questions. One LLM call.
_rg = StateGraph(ResumeState)
_rg.add_node("rate", rate_node)
_rg.add_edge(START, "rate")
_rg.add_edge("rate", END)
rate_only_graph = _rg.compile()

_og = StateGraph(OptimizerState)
_og.add_node("optimize", optimize_node)
_og.add_edge(START, "optimize")
_og.add_edge("optimize", END)
optimizer_graph = _og.compile()
