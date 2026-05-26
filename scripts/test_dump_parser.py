"""
test_dump_parser.py
==================
Offline test for the Claude-based dump extractor.

We stub out the Anthropic client with a fake that returns a deterministic
response, so the test verifies:

  * we send a properly-shaped request (prompt-cached system, json_schema
    output_config, the dumped text in the user turn),
  * we correctly turn the JSON response into a LEAD_SCHEMA-shaped frame.

To test against the *real* Claude API instead, set ANTHROPIC_API_KEY in
your environment and call `dump_parser.parse_dump()` directly from a REPL.

Run:
    python -m scripts.test_dump_parser
"""

import io
import json
from types import SimpleNamespace
from unittest.mock import patch

from app.config.constants import LEAD_SCHEMA
from app.ingestion import dump_parser

SAMPLE_TEXT = """\
Met Dave Otway at the food show - he runs Crepe Cuisine
(http://www.crepecuisine.com/). Worth a follow-up.

Also: Jane Lee, Maintenance Manager at Acme Industrial,
jane.lee@acme-ind.com. Based in Manchester.
"""

# What a real Claude response would look like (modulo wrapping).
_FAKE_RESPONSE_JSON = json.dumps({
    "leads": [
        {
            "full_name": "Dave Otway",
            "first_name": "Dave",
            "last_name": "Otway",
            "company": "Crepe Cuisine",
            "role": "",
            "email": "",
            "linkedin_profile": "",
            "location": "",
            "notes": "Met at food show. Website: http://www.crepecuisine.com/",
        },
        {
            "full_name": "Jane Lee",
            "first_name": "Jane",
            "last_name": "Lee",
            "company": "Acme Industrial",
            "role": "Maintenance Manager",
            "email": "jane.lee@acme-ind.com",
            "linkedin_profile": "",
            "location": "Manchester",
            "notes": "",
        },
    ]
})


class _FakeAnthropic:
    """Stand-in client whose .messages.create returns a canned response."""

    def __init__(self):
        self.last_call: dict | None = None

        text_block = SimpleNamespace(type="text", text=_FAKE_RESPONSE_JSON)
        usage = SimpleNamespace(
            input_tokens=120,
            output_tokens=80,
            cache_creation_input_tokens=0,
            cache_read_input_tokens=0,
        )
        response = SimpleNamespace(content=[text_block], usage=usage)

        class _Messages:
            def create(inner_self, **kwargs):
                self.last_call = kwargs
                return response

        self.messages = _Messages()


def main() -> None:
    print("LOBO AI Leads — dump parser test")
    print("=" * 55)

    fake_client = _FakeAnthropic()

    # The parser refuses to run without an API key, so set a fake one.
    # Also patch anthropic.Anthropic() to return our fake client.
    with patch.object(dump_parser.settings, "ANTHROPIC_API_KEY", "sk-test"), \
         patch("app.ingestion.dump_parser.anthropic.Anthropic",
                return_value=fake_client):
        df = dump_parser.parse_dump(
            "notes.txt", io.BytesIO(SAMPLE_TEXT.encode("utf-8"))
        )

    # --- Verify request shape ----------------------------------------
    call = fake_client.last_call
    assert call["model"] == "claude-opus-4-7", call["model"]
    assert isinstance(call["system"], list), "system should be a list (for cache_control)"
    assert call["system"][0]["cache_control"] == {"type": "ephemeral"}, \
        "prompt caching must be enabled on system prompt"
    assert call["output_config"]["format"]["type"] == "json_schema", \
        "must use json_schema structured output"
    assert "Source: notes.txt" in call["messages"][0]["content"], \
        "filename should be passed to the model for context"
    print("[OK] Request shape: opus-4-7, cached system, json_schema, user content present.")

    # --- Verify output frame -----------------------------------------
    assert list(df.columns) == LEAD_SCHEMA, "columns must match LEAD_SCHEMA"
    assert len(df) == 2
    assert set(df["full_name"]) == {"Dave Otway", "Jane Lee"}
    # Website went to notes, not linkedin_profile.
    dave = df[df["full_name"] == "Dave Otway"].iloc[0]
    assert "crepecuisine.com" in dave["notes"]
    assert dave["linkedin_profile"] == ""
    print(f"[OK] Output frame: {len(df)} rows, schema matches.")
    print(df[["full_name", "company", "role", "email"]].to_string(index=False))

    # --- Verify no-API-key behaviour ---------------------------------
    with patch.object(dump_parser.settings, "ANTHROPIC_API_KEY", ""):
        empty = dump_parser.parse_dump("notes.txt", io.BytesIO(b"some text"))
    assert empty.empty and list(empty.columns) == LEAD_SCHEMA
    print("[OK] Disabled gracefully when ANTHROPIC_API_KEY is unset.")

    print("=" * 55)
    print("SUCCESS: dump parser extracts leads from free-text into LEAD_SCHEMA.")


if __name__ == "__main__":
    main()
