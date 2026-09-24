import os
import json
import re
from typing import Dict, List, Any, Optional
from groq import Groq

MAX_SOURCE_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "50000"))

OUTPUT_NAMES = {
    "linkedin": "LinkedIn Post",
    "x": "X/Twitter Thread",
    "advisory": "Advisory",
    "summary": "Executive Summary",
    "presentation": "Presentation",
    "infographic": "Infographic",
    "video": "Video Package",
}


def _trim(text: str) -> str:
    return text[:MAX_SOURCE_CHARS]


def _demo_outputs(source: str, outputs: List[str], settings: Dict[str, str]) -> Dict[str, Any]:
    title = _make_title(source)
    facts = _extract_facts(source)
    bullets = facts[:5] if facts else ["Key information extracted from the supplied source."]

    result = {}
    for key in outputs:
        if key == "linkedin":
            result[key] = {
                "title": title,
                "content": (
                    f"{title}\n\n"
                    f"{source[:900].strip()}\n\n"
                    "#AI #Innovation #Technology"
                ),
                "source_basis": bullets,
            }
        elif key == "x":
            result[key] = {
                "title": "X/Twitter Thread",
                "posts": [
                    f"1/ {title}",
                    f"2/ {bullets[0] if bullets else source[:240]}",
                    f"3/ {bullets[1] if len(bullets) > 1 else 'Here are the key implications and actions.'}",
                    "4/ The main takeaway is to turn the source information into clear, actionable communication.",
                ],
            }
        elif key == "advisory":
            result[key] = {
                "title": title,
                "sections": [
                    {"heading": "Purpose", "body": source[:700].strip()},
                    {"heading": "Key Findings", "body": "\n".join(f"• {x}" for x in bullets)},
                    {"heading": "Recommended Actions", "body": "• Review the source findings\n• Communicate relevant impacts to stakeholders\n• Track follow-up actions"},
                ],
            }
        elif key == "summary":
            result[key] = {
                "title": title,
                "summary": source[:1500].strip(),
                "key_points": bullets,
                "implications": "The source should be reviewed in its operational context before decisions are taken.",
            }
        elif key == "presentation":
            slides = [
                {"title": title, "bullets": [f"Audience: {settings['audience']}", f"Objective: {settings['objective']}"]},
                {"title": "Context", "bullets": bullets[:3]},
                {"title": "Key Findings", "bullets": bullets},
                {"title": "Implications", "bullets": ["What changes?", "Who is affected?", "What should happen next?"]},
                {"title": "Action Plan", "bullets": ["Prioritize key actions", "Assign owners", "Monitor outcomes"]},
            ]
            result[key] = {"title": title, "slides": slides, "speaker_notes": ["Explain the context.", "Walk through the evidence.", "Close with actions."]}
        elif key == "infographic":
            result[key] = {
                "title": title,
                "headline": title,
                "sections": [
                    {"label": "What happened?", "points": bullets[:2]},
                    {"label": "Why it matters", "points": bullets[2:4] or ["Relevant implications"]},
                    {"label": "What to do", "points": ["Review", "Communicate", "Act"]},
                ],
                "layout": "Top headline → three horizontal sections → final call-to-action.",
            }
        elif key == "video":
            result[key] = {
                "title": title,
                "duration": "60–90 seconds",
                "narration": source[:1200].strip(),
                "scenes": [
                    {"scene": 1, "visual": "Opening title and source context", "narration": title},
                    {"scene": 2, "visual": "Show the key facts as animated cards", "narration": bullets[0] if bullets else "Key finding"},
                    {"scene": 3, "visual": "Show implications and actions", "narration": "Focus on the practical takeaway and next steps."},
                ],
                "subtitles": [title] + bullets,
            }
    return result


def _make_title(source: str) -> str:
    first = re.sub(r"\s+", " ", source.strip()).split(".")[0]
    return (first[:90] + "…") if len(first) > 90 else (first or "Source Content")


def _extract_facts(source: str) -> List[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", source) if len(s.strip()) > 30]
    return sentences[:8]


def _groq_outputs(
    source: str,
    outputs: List[str],
    settings: Dict[str, str],
    image_data_url: Optional[str] = None,
) -> Dict[str, Any]:
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    output_schema = {
        key: (
            "Return an object with title, content, and source_basis."
            if key == "linkedin" else
            "Return an object with title and posts (array of strings)."
            if key == "x" else
            "Return an object with title and sections (array of {heading, body})."
            if key == "advisory" else
            "Return an object with title, summary, key_points (array), and implications."
            if key == "summary" else
            "Return an object with title, slides (array of {title, bullets}), and speaker_notes (array)."
            if key == "presentation" else
            "Return an object with title, headline, sections (array of {label, points}), and layout."
            if key == "infographic" else
            "Return an object with title, duration, narration, scenes (array of {scene, visual, narration}), and subtitles (array)."
            if key == "video" else
            "Return a JSON object."
        )
        for key in outputs
    }

    system = """You are ContentForge AI, a professional content transformation engine.
Transform the provided source into the requested communication artefacts.

IMPORTANT:
- If an image is supplied, inspect the actual image. Read visible text, headings,
  numbers, charts and relevant visual context. Perform visual understanding/OCR.
- Do not treat the filename or image dimensions as the content.
- Do not invent facts, names, numbers, quotes, dates, or citations.
- If something is unreadable, say it is unavailable.
- Use the same verified source facts across every selected output.
- Make outputs polished and publication-ready.
- Respect audience, tone, language, detail, objective and style.
- Return VALID JSON ONLY with an object named "outputs".
"""

    user_content = [{
        "type": "text",
        "text": json.dumps({
            "source_text": source,
            "settings": settings,
            "requested_outputs": {k: OUTPUT_NAMES.get(k, k) for k in outputs},
            "schema": output_schema,
        }, ensure_ascii=False)
    }]
    if image_data_url:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": image_data_url}
        })

    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user_content},
        ],
    )
    data = json.loads(response.choices[0].message.content)
    return data.get("outputs", data)

def generate_outputs(source_text: str, outputs: List[str], audience: str, tone: str,
                     language: str, detail: str, objective: str, style: str,
                     image_data_url: Optional[str] = None):
    valid = [x for x in outputs if x in OUTPUT_NAMES]
    if not valid:
        raise ValueError("Select at least one valid output type.")

    settings = {
        "audience": audience,
        "tone": tone,
        "language": language,
        "detail": detail,
        "objective": objective,
        "style": style,
    }

    if os.getenv("GROQ_API_KEY"):
        try:
            generated = _groq_outputs(source_text, valid, settings)
            mode = "groq"
        except Exception as exc:
            # Graceful fallback keeps the demo usable if the provider is unavailable.
            generated = _demo_outputs(source_text, valid, settings)
            generated["_warning"] = f"AI provider unavailable; demo mode used. Reason: {type(exc).__name__}"
            mode = "demo-fallback"
    else:
        generated = _demo_outputs(source_text, valid, settings)
        mode = "demo"

    return {
        "mode": mode,
        "source": {
            "chars": len(source_text),
            "preview": source_text[:700],
            "outputs_requested": valid,
        },
        "outputs": generated,
    }
