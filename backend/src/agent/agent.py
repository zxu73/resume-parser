import os
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
import litellm

_BULLET_GUIDELINES = (Path(__file__).parent / "guidelines.md").read_text(encoding="utf-8")

litellm.api_key = os.getenv("OPENAI_API_KEY", "")

def _model() -> LiteLlm:
    """Return a LiteLlm instance for the configured reasoning model."""
    return LiteLlm(model=f"openai/{os.getenv('REASONING_MODEL', 'gpt-4o-mini')}")

# ── Evaluation Agent schema ──────────────────────────────────────────────

class EvaluationResponse(BaseModel):
    executive_summary: str
    overall_score: float = Field(..., ge=1, le=10)
    job_match_percentage: float = Field(..., ge=0, le=100)
    strengths: List[str]
    weaknesses: List[str]
    missing_skills: List[str]
    matching_skills: List[str]

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

    @model_validator(mode="after")
    def keywords_must_appear_in_suggested_text(self) -> "ParaphrasingSuggestion":
        missing = [kw for kw in self.keywords_added if kw not in self.suggested_text]
        if missing:
            raise ValueError(
                f"keywords_added entries {missing} do not appear as literal substrings "
                f"in suggested_text. Either embed each keyword word-for-word in "
                f"suggested_text or remove it from keywords_added."
            )
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
    def validate_suggestion_types(self) -> "RatingResponse":
        for i, rec in enumerate(self.keyword_suggestions):
            if not rec.paraphrasing_suggestion.keywords_added:
                raise ValueError(
                    f"keyword_suggestions[{i}] must have non-empty keywords_added — "
                    "this section is for missing-skill insertion only."
                )
        for i, rec in enumerate(self.star_suggestions):
            if rec.paraphrasing_suggestion.keywords_added:
                raise ValueError(
                    f"star_suggestions[{i}] must have keywords_added: [] — "
                    "this section is for STAR/clarity improvements only, no keyword insertion."
                )
        keyword_texts = {
            rec.paraphrasing_suggestion.current_text.strip()
            for rec in self.keyword_suggestions
        }
        for i, rec in enumerate(self.star_suggestions):
            if rec.paraphrasing_suggestion.current_text.strip() in keyword_texts:
                raise ValueError(
                    f"star_suggestions[{i}] targets a bullet already covered by keyword_suggestions. "
                    "Each bullet must appear in exactly one section."
                )
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

# ── Agents ───────────────────────────────────────────────────────────────

evaluation_agent = LlmAgent(
    name="resume_evaluation_agent",
    model=_model(),
    output_schema=EvaluationResponse,
    instruction=(
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
        "7. matching_skills — skills present in both resume and JD.\n\n"

        "=== GUIDELINES ===\n"
        "- Do NOT recommend adding a Professional Summary.\n"
        "- For missing_skills, go beyond obvious ones — include specific tools, certifications,\n"
        "  methodologies, and soft skills mentioned in the JD.\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching the schema."
    ),
    description="Evaluates resumes and identifies missing skills for the rewriting agent.",
    tools=[],
)

experience_optimizer_agent = LlmAgent(
    name="experience_optimizer_agent",
    model=_model(),
    output_schema=SmartExperienceOptimization,
    instruction=(
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
    ),
    description="Swaps experiences when pool entries better match the JD and show stronger skill evidence.",
    tools=[],
)

rating_agent = LlmAgent(
    name="resume_rating_and_generation_agent",
    model=_model(),
    output_schema=RatingResponse,
    instruction=(
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

        "=== SECTION 2: PER-BULLET DECISION PASS ===\n"
        "You will receive MISSING SKILLS from the evaluation agent.\n"
        "Visit every bullet in the resume exactly once, in order. For each bullet apply\n"
        "exactly ONE rule — never both, never the same bullet in both output lists.\n\n"

        "RULE A → emit into keyword_suggestions (target 10-15 items total):\n"
        "  Condition: at least one MISSING SKILL can be honestly woven into this bullet.\n"
        "  Be GENEROUS — if the bullet describes work that could plausibly involve\n"
        "  a JD skill, insert it. The candidate likely used it but didn't name it.\n"
        "  Action: rewrite the bullet in full STAR format AND embed every fitting missing\n"
        "  skill verbatim. List each in keywords_added (each must be a literal substring\n"
        "  of suggested_text). keywords_added must be non-empty.\n\n"

        "RULE B → emit into star_suggestions (target 5-10 items total):\n"
        "  Condition: no missing skill plausibly fits this bullet AND it can be meaningfully\n"
        "  improved (vague, weak verb, lacks a result, no STAR structure, buries impact).\n"
        "  Action: rewrite in full STAR format only. keywords_added must be [].\n"
        "  Do NOT apply if the bullet is already clear and well-structured.\n\n"

        "SKIP: no missing skill fits AND the bullet is already strong → do not emit it.\n\n"

        "NO DUPLICATES: Each bullet's current_text must appear in at most one section.\n"
        "Never suggest changes to the same bullet twice.\n\n"

        "KEYWORD COVERAGE: after the per-bullet pass, check which missing skills are still\n"
        "unplaced. For each unplaced skill, find the best already-selected Rule-A bullet\n"
        "that can carry it and add it there. Each missing skill should appear in AT MOST\n"
        "2 keyword_suggestions entries.\n\n"

        "ATS KEYWORD RULES (when keywords_added is non-empty — verify before you output JSON):\n"
        "- Pick keywords ONLY from the MISSING SKILLS list. Copy each chosen string CHARACTER-FOR-CHARACTER.\n"
        "- If keywords_added is empty, skip this block — no JD keyword claims in alignment_reason.\n"
        "- If keywords_added has entries: suggested_text MUST contain every one as a LITERAL SUBSTRING.\n"
        "  Example: if keywords_added contains \"PyTorch\", suggested_text must include the exact token PyTorch.\n"
        "- alignment_reason and suggested_text must agree: every term you say you incorporated must appear\n"
        "  in suggested_text as that EXACT substring (word-for-word), and must be one of keywords_added.\n"
        "  Wrong: keywords_added has \"REST APIs\" but you write \"web APIs\" in suggested_text and claim REST in why.\n"
        "  Right: suggested_text contains the literal substring \"REST APIs\" and alignment_reason quotes that same string.\n"
        "- Do not describe a keyword in alignment_reason that is missing from suggested_text.\n"
        "- Use the EXACT JD wording, not synonyms (ATS literal match).\n"
        "  Bad: list \"Kubernetes\" in keywords_added but write \"container orchestration\" only.\n"
        "  Good: write \"... deployed services on Kubernetes ...\" and list \"Kubernetes\".\n"
        "- Before returning JSON, mentally verify: for each item K in keywords_added, suggested_text.includes(K).\n\n"

        "OTHER RULES (apply to both sections):\n"
        "1. Every suggestion MUST include a paraphrasing_suggestion. Never omit it.\n"
        "2. NEVER invent entire projects or job responsibilities. But DO name JD skills when the bullet's context plausibly involves them.\n"
        "3. For each: priority | title (exact job title from resume) | description | specific_example\n"
        "4. paraphrasing_suggestion fields:\n"
        "   current_text — copy the bullet character-for-character (include bullet symbol)\n"
        "   suggested_text — STAR format; keyword_suggestions: embed exact keyword strings; star_suggestions: STAR-only polish, no keywords\n"
        "   keywords_added — keyword_suggestions: exact copy from MISSING SKILLS, each a substring of suggested_text; star_suggestions: always []\n"
        "   job_requirement_reference — quote the JD sentence this bullet better addresses\n"
        "   alignment_reason — keyword_suggestions: explicitly name each keyword incorporated,\n"
        "     e.g. 'Incorporated missing JD skill \"REST APIs\" to highlight API development experience.'\n"
        "     List every keyword from keywords_added by name so the user sees exactly which missing skills were added.\n"
        "     star_suggestions: describe only STAR/impact improvements, do not mention JD keywords\n\n"

        "Do NOT recommend adding a professional summary.\n\n"

        "OUTPUT FORMAT: Return ONLY valid JSON matching RatingResponse schema.\n"
        "The JSON must have keys: detailed_ratings, keyword_suggestions, star_suggestions."
    ),
    description="Rewrites resume bullets: adds missing JD keywords or improves STAR format.",
    tools=[],
)
