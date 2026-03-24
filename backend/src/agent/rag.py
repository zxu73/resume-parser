"""RAG module for retrieving strong resume bullet examples before rewriting."""

import json
import os
import re
from pathlib import Path
from typing import Optional

import chromadb
from chromadb import Collection
from dotenv import load_dotenv
from google.genai.client import Client

load_dotenv()

_CORPUS_PATH = Path(__file__).parent.parent.parent.parent / "data" / "strong_bullets.json"
_CHROMA_DIR = Path(__file__).parent.parent.parent.parent / ".chroma"
_COLLECTION_NAME = "strong_bullets"
_EMBEDDING_MODEL = "text-embedding-004"

_client: Optional[Client] = None
_collection: Optional[Collection] = None


def _get_genai_client() -> Client:
    global _client
    if _client is None:
        _client = Client(api_key=os.getenv("GEMINI_API_KEY"))
    return _client


def _embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using Google text-embedding-004."""
    genai = _get_genai_client()
    result = genai.models.embed_content(
        model=_EMBEDDING_MODEL,
        contents=texts,
    )
    return [e.values for e in result.embeddings]


def build_or_load_collection() -> Collection:
    """Return the ChromaDB collection, building and indexing it if not yet persisted."""
    global _collection
    if _collection is not None:
        return _collection

    chroma_client = chromadb.PersistentClient(path=str(_CHROMA_DIR))

    existing = [c.name for c in chroma_client.list_collections()]
    if _COLLECTION_NAME in existing:
        _collection = chroma_client.get_collection(_COLLECTION_NAME)
        return _collection

    corpus = json.loads(_CORPUS_PATH.read_text(encoding="utf-8"))

    texts = [item["text"] for item in corpus]
    ids = [f"bullet_{i}" for i in range(len(texts))]
    metadatas = [
        {"role": item.get("role", ""), "skills": ", ".join(item.get("skills", []))}
        for item in corpus
    ]

    print(f"[RAG] Indexing {len(texts)} bullets into ChromaDB...")
    embeddings = _embed(texts)

    _collection = chroma_client.create_collection(
        name=_COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    _collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    print(f"[RAG] Collection built and persisted to {_CHROMA_DIR}")
    return _collection


def _build_query(bullet: str, missing_skills: list[str], job_description: str) -> str:
    """Build a rich query string combining bullet text, missing skills, and job context."""
    parts = [bullet.strip()]
    if missing_skills:
        parts.append(f"Target skills: {', '.join(missing_skills[:8])}")
    if job_description:
        # Use only the first 300 chars of JD to avoid noise
        jd_snippet = job_description.strip()[:300].replace("\n", " ")
        parts.append(f"Job context: {jd_snippet}")
    return "\n".join(parts)


def extract_resume_bullets(resume_text: str) -> list[str]:
    """Extract individual bullet points or sentences from a resume.

    Returns a list of up to 15 non-trivial lines/bullets from the work experience.
    """
    bullets = []
    for line in resume_text.splitlines():
        line = line.strip()
        # Strip common bullet markers
        clean = re.sub(r"^[\•\-\*\>\·]\s*", "", line).strip()
        # Keep lines with meaningful length (likely actual bullets, not headers)
        if 30 <= len(clean) <= 300:
            bullets.append(clean)
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique = []
    for b in bullets:
        if b not in seen:
            seen.add(b)
            unique.append(b)
    return unique[:15]


def retrieve_similar_bullets(
    query: str,
    k: int = 3,
    missing_skills: Optional[list[str]] = None,
    job_description: str = "",
) -> list[str]:
    """Return the k most semantically similar strong bullets for a single query.

    Args:
        query: A resume bullet or sentence to find examples for.
        k: Number of examples to retrieve.
        missing_skills: Optional list of skills to add context to the query.
        job_description: Optional JD snippet to further sharpen the query.

    Returns:
        List of strong bullet strings ordered by similarity.
    """
    try:
        collection = build_or_load_collection()
        rich_query = _build_query(query, missing_skills or [], job_description)
        query_embedding = _embed([rich_query])[0]
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=k,
            include=["documents"],
        )
        return results["documents"][0] if results["documents"] else []
    except Exception as e:
        print(f"[RAG] Retrieval failed for query '{query[:60]}...': {e}")
        return []


def retrieve_per_bullet(
    resume_text: str,
    missing_skills: list[str],
    job_description: str,
    k: int = 3,
) -> dict[str, list[str]]:
    """Retrieve strong example bullets for each bullet extracted from the resume.

    Batches all bullet embeddings in a single API call for efficiency.

    Args:
        resume_text: Full resume text to extract bullets from.
        missing_skills: Skills identified as missing (from evaluation agent).
        job_description: The target job description.
        k: Number of examples to retrieve per bullet.

    Returns:
        Dict mapping each original bullet to a list of strong example bullets.
    """
    bullets = extract_resume_bullets(resume_text)
    if not bullets:
        return {}

    try:
        collection = build_or_load_collection()

        # Build rich queries for all bullets at once
        queries = [_build_query(b, missing_skills, job_description) for b in bullets]

        # Single batched embedding call for all bullets
        print(f"[RAG] Embedding {len(queries)} bullets in one batch...")
        all_embeddings = _embed(queries)

        result_map: dict[str, list[str]] = {}
        for bullet, embedding in zip(bullets, all_embeddings):
            results = collection.query(
                query_embeddings=[embedding],
                n_results=k,
                include=["documents"],
            )
            examples = results["documents"][0] if results["documents"] else []
            result_map[bullet] = examples

        print(f"[RAG] Retrieved examples for {len(result_map)} bullets")
        return result_map

    except Exception as e:
        print(f"[RAG] Per-bullet retrieval failed: {e}")
        return {}



def format_rag_context(bullet_examples: dict[str, list[str]]) -> str:
    """Format per-bullet RAG results into a prompt-ready string block.

    Args:
        bullet_examples: Output from retrieve_per_bullet().

    Returns:
        Formatted string to inject into the rating agent prompt.
    """
    if not bullet_examples:
        return ""

    lines = [
        "==================== STRONG BULLET EXAMPLES (RAG) ====================",
        "For each original resume bullet below, strong example rewrites are provided.",
        "Use these ONLY as style and structure references — do NOT copy metrics or technologies the user has not mentioned.",
        "",
    ]

    for i, (bullet, examples) in enumerate(bullet_examples.items(), 1):
        lines.append(f"Original bullet {i}: \"{bullet}\"")
        lines.append("Strong examples for style reference:")
        for ex in examples:
            lines.append(f"  - {ex}")
        lines.append("")

    lines.append("==================== END OF RAG EXAMPLES ====================")
    return "\n".join(lines)


def select_weak_bullets_with_agent(
    resume_text: str,
    job_description: str,
    missing_skills: list[str],
    top_k: int = 7,
) -> list[str]:
    """Use Gemini to identify the top_k weakest bullets relative to the job description.

    The model judges weakness in context — it understands which bullets are
    irrelevant, vague, or missing JD keywords relative to THIS specific job,
    not just by generic rules.

    Falls back to rule-based extraction if the agent call fails.

    Args:
        resume_text: Full resume text.
        job_description: Target job description.
        missing_skills: Skills missing from the resume (from evaluation agent).
        top_k: Number of weak bullets to return.

    Returns:
        List of exact bullet strings from the resume, ordered weakest-first.
    """
    bullets = extract_resume_bullets(resume_text)
    if not bullets:
        return []

    bullets_numbered = "\n".join(f"{i + 1}. {b}" for i, b in enumerate(bullets))
    missing_str = ", ".join(missing_skills[:10]) if missing_skills else "none identified"

    prompt = f"""You are a resume coach reviewing bullets against a specific job description.

RESUME BULLETS (numbered):
{bullets_numbered}

JOB DESCRIPTION:
{job_description[:600]}

MISSING SKILLS (in JD but absent from resume):
{missing_str}

TASK:
Identify the {top_k} bullets that most need rewriting to better match this job.
Judge weakness by:
- Missing JD keywords or required skills
- Vague language with no technical detail
- No quantified result or impact
- Weak or missing action verb
- Low relevance to the job requirements

RULES:
- Return ONLY a valid JSON array of the exact bullet strings
- Copy each bullet CHARACTER-BY-CHARACTER from the numbered list above — no changes
- Order from weakest (index 0) to least weak (last)
- No explanation, no extra text — only the JSON array

EXAMPLE FORMAT:
["weakest bullet text here", "second weakest here", ...]

WEAKEST {top_k} BULLETS JSON:"""

    try:
        genai = _get_genai_client()
        from google.genai import types as genai_types
        response = genai.models.generate_content(
            model=os.getenv("REASONING_MODEL", "gemini-2.5-flash"),
            contents=[genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)])],
        )
        raw = response.text.strip()

        # Strip markdown code fences if present
        if "```" in raw:
            raw = re.sub(r"```(?:json)?", "", raw).replace("```", "").strip()

        selected: list[str] = json.loads(raw)

        # Validate: every returned bullet must exist verbatim in the extracted list
        valid = [b for b in selected if b in bullets]
        if valid:
            print(f"[RAG] Agent identified {len(valid)} weak bullets for rewriting")
            return valid[:top_k]

        print("[RAG] Agent selection invalid, falling back to first N bullets")
        return bullets[:top_k]

    except Exception as e:
        print(f"[RAG] Agent selection failed ({e}), using first N bullets as fallback")
        return bullets[:top_k]


def retrieve_examples_for_weak_bullets(
    weak_bullets: list[str],
    missing_skills: list[str],
    job_description: str,
    k: int = 3,
) -> dict[str, list[str]]:
    """Retrieve strong RAG templates for a pre-selected list of weak bullets.

    Batches all embeddings into a single API call for efficiency.

    Returns:
        Dict mapping each weak bullet → list of k strong example bullets.
    """
    if not weak_bullets:
        return {}
    try:
        collection = build_or_load_collection()
        queries = [_build_query(b, missing_skills, job_description) for b in weak_bullets]
        print(f"[RAG] Batch-embedding {len(queries)} weak bullets...")
        all_embeddings = _embed(queries)

        result_map: dict[str, list[str]] = {}
        for bullet, embedding in zip(weak_bullets, all_embeddings):
            results = collection.query(
                query_embeddings=[embedding],
                n_results=k,
                include=["documents"],
            )
            result_map[bullet] = results["documents"][0] if results["documents"] else []

        print(f"[RAG] Retrieved templates for {len(result_map)} weak bullets")
        return result_map
    except Exception as e:
        print(f"[RAG] retrieve_examples_for_weak_bullets failed: {e}")
        return {}


def format_rag_for_rating_prompt(
    bullet_examples: dict[str, list[str]],
    missing_skills: list[str],
) -> str:
    """Format weak bullets + RAG templates into a block ready for the rating agent prompt.

    Each weak bullet is shown with its retrieved strong templates so the rating
    agent can model its suggested_text rewrites directly on them.
    """
    if not bullet_examples:
        return ""

    lines = [
        "==================== PRE-SELECTED WEAK BULLETS + RAG TEMPLATES ====================",
        "These bullets were identified as weakest relative to the job description.",
        "Focus your paraphrasing_suggestion recommendations on THESE bullets.",
        "Use the strong templates for STYLE and STRUCTURE only.",
        "Do NOT copy their metrics or technologies unless the user has demonstrated them.",
        "",
    ]

    for i, (bullet, examples) in enumerate(bullet_examples.items(), 1):
        missing_here = [s for s in missing_skills[:6] if s.lower() not in bullet.lower()]
        lines.append(f"Weak bullet {i}: \"{bullet}\"")
        if missing_here:
            lines.append(f"Missing JD skills to integrate: {', '.join(missing_here)}")
        lines.append("Strong templates (style reference):")
        for ex in examples:
            lines.append(f"  - {ex}")
        lines.append("")

    lines.append("==================== END OF RAG TEMPLATES ====================")
    return "\n".join(lines)
