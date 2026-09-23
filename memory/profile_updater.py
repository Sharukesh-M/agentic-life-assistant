import json

from llm_client import ask_gemini
from profile_manager import (
    load_profile,
    update_profile
)


def extract_profile_updates(
    user_message: str
) -> dict:

    profile = load_profile()

    prompt = f"""
You are the profile manager for a personal AI assistant.

You must identify information in the user's latest
message that should update their structured profile.

CURRENT PROFILE:

{json.dumps(profile, indent=2)}

USER MESSAGE:

{user_message}

Only extract information that is:

- explicitly stated by the user
- useful in future conversations
- reasonably persistent
- relevant to personalization

Do NOT store temporary information.

Examples of useful information:

- education
- profession
- current goals
- interests
- skills
- preferences
- important context

Return ONLY JSON.

Use this structure:

{{
    "identity": {{}},
    "role": {{}},
    "education": {{}},
    "profession": {{}},
    "preferences": {{}},
    "interests": [],
    "skills": [],
    "important_context": {{}}
}}

If there is nothing to update, return empty sections.

Do not invent information.
"""

    result = ask_gemini(prompt)

    result = (
        result
        .replace("```json", "")
        .replace("```", "")
        .strip()
    )

    try:
        return json.loads(result)

    except json.JSONDecodeError:
        return {}
def update_profile_from_message(
    user_message: str
):

    updates = extract_profile_updates(
        user_message
    )

    if not updates:
        return None

    return update_profile(updates)