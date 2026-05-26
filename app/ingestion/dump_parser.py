"""
dump_parser.py
=============
Free-text lead extractor for 07_RAW_DUMP.

Hands a dropped .txt / .md file to Claude (`claude-opus-4-7`) and asks it
to pull out anything that looks like a lead — names, companies, roles,
emails, URLs. The response is constrained to a strict JSON schema via
the `output_config.format` parameter, so we don't have to parse free-form
model output.

Why Claude over regex
---------------------
Regex catches "First Last <email@domain>" but misses messy real-world
notes ("met Dave at the show, runs the Crepe Cuisine place"). The brief
asked for the higher-accuracy option; this is it.

Cost discipline
---------------
* The system prompt (instructions + schema rules) is **prompt-cached** —
  every file after the first reuses the cached prefix at ~10% of input cost.
* Effort is set to `medium`: extraction is structured and bounded, not an
  intelligence-sensitive agentic task. (`high` would burn tokens with no
  measurable quality gain here.)

What this module does NOT do
----------------------------
No cleaning, validation, dedupe, or scoring — same as `linkedin_parser`.
It returns a LEAD_SCHEMA-shaped frame; the rest of the pipeline takes it
from there.
"""

import io

import anthropic
import pandas as pd

from app.config import settings
from app.config.constants import LEAD_SCHEMA
from app.logs.logger import get_logger

log = get_logger(__name__)

# Maximum text we'll send to the model. Beyond this, we truncate with a
# notice — most "dumped" notes are short, and silently sending megabytes
# would be both slow and expensive.
_MAX_INPUT_CHARS = 50_000

# Stable extraction brief. Anything that changes between files (the text
# itself) goes in the user turn so the cache prefix stays identical.
_SYSTEM_PROMPT = """\
You extract sales leads from unstructured notes and return STRICT JSON.

For each distinct person or organisation that could be a sales lead, emit
one object with these fields (use an empty string for anything you cannot
confidently determine — do not invent values):

  - full_name         person's full name as written
  - first_name        first/given name only
  - last_name         family/surname only
  - company           employer or organisation
  - role              job title or function
  - email             a syntactically valid email address, or ""
  - linkedin_profile  a linkedin.com/in/... URL, or "" (do NOT put website
                      URLs here — those belong in `notes`)
  - location          city, region, or country if mentioned
  - notes             anything else worth preserving (website URL, context,
                      how they were met, etc.)

Rules:
  * Return ONLY leads. Skip generic content (news headlines, agendas, …).
  * Each row must be a distinct lead. Do not duplicate.
  * Prefer empty strings over guesses. Empty is fine; wrong is costly.
  * If no leads are present, return an empty `leads` array.
"""

# JSON schema that Claude's response is constrained to. The empty-string
# defaults + `required` on every field guarantee a uniform shape we can
# safely splat into a DataFrame.
_EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "leads": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "full_name": {"type": "string"},
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "company": {"type": "string"},
                    "role": {"type": "string"},
                    "email": {"type": "string"},
                    "linkedin_profile": {"type": "string"},
                    "location": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": [
                    "full_name", "first_name", "last_name", "company",
                    "role", "email", "linkedin_profile", "location", "notes",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["leads"],
    "additionalProperties": False,
}


def _empty_frame() -> pd.DataFrame:
    """Schema-shaped empty frame — the contract every parser returns."""
    return pd.DataFrame(columns=LEAD_SCHEMA)


def _read_text(buffer: io.BytesIO) -> str:
    """Decode the dumped file as UTF-8 (best-effort) and bound its size."""
    buffer.seek(0)
    text = buffer.read().decode("utf-8", errors="replace").strip()
    if len(text) > _MAX_INPUT_CHARS:
        log.warning(
            "Dump file truncated to %d chars (was %d)",
            _MAX_INPUT_CHARS, len(text),
        )
        text = text[:_MAX_INPUT_CHARS]
    return text


def parse_dump(filename: str, buffer: io.BytesIO) -> pd.DataFrame:
    """
    Extract leads from a free-text dump file and return a LEAD_SCHEMA frame.

    If `ANTHROPIC_API_KEY` is not set, the extractor is disabled and the
    function returns an empty frame (the caller will still archive/audit).
    """
    if not settings.ANTHROPIC_API_KEY:
        log.warning(
            "[dump_parser] ANTHROPIC_API_KEY not set — leaving '%s' unextracted.",
            filename,
        )
        return _empty_frame()

    text = _read_text(buffer)
    if not text:
        log.info("[dump_parser] '%s' was empty.", filename)
        return _empty_frame()

    client = anthropic.Anthropic()

    # `messages.create` with `output_config.format` is the canonical
    # structured-output path. The response's first text block is guaranteed
    # to be valid JSON matching the schema above.
    response = client.messages.create(
        model=settings.ANTHROPIC_MODEL,
        max_tokens=16000,
        # Prompt caching: the system prompt is stable across every file, so
        # we mark it cacheable. Every file after the first hits the cache.
        system=[{
            "type": "text",
            "text": _SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }],
        output_config={
            "format": {"type": "json_schema", "schema": _EXTRACTION_SCHEMA},
            "effort": "medium",  # extraction isn't an intelligence-heavy task
        },
        messages=[{
            "role": "user",
            "content": f"Source: {filename}\n\n---\n{text}",
        }],
    )

    # Log cache effectiveness so we can see savings in production logs.
    usage = response.usage
    log.info(
        "[dump_parser] '%s': in=%d cache_read=%d cache_write=%d out=%d",
        filename,
        usage.input_tokens,
        getattr(usage, "cache_read_input_tokens", 0) or 0,
        getattr(usage, "cache_creation_input_tokens", 0) or 0,
        usage.output_tokens,
    )

    # output_config.format guarantees the first content block is JSON text.
    import json
    raw_json = next(b.text for b in response.content if b.type == "text")
    data = json.loads(raw_json)
    leads = data.get("leads", [])

    if not leads:
        log.info("[dump_parser] No leads found in '%s'.", filename)
        return _empty_frame()

    # Build the schema-shaped frame. Fields the extractor doesn't fill
    # (connection_date / lead_score / lead_priority) stay blank for the
    # downstream stages to populate.
    df = pd.DataFrame(leads)
    for col in LEAD_SCHEMA:
        if col not in df.columns:
            df[col] = ""
    log.info("[dump_parser] Extracted %d lead(s) from '%s'.", len(df), filename)
    return df[LEAD_SCHEMA]
