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
    """Two-stage pipeline:
    1) Build a source-intelligence brief from the actual source/image.
    2) Transform that verified brief into every requested artefact.
    """
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

    # ---------- Stage 1: source intelligence ----------
    analysis_prompt = """You are the Source Intelligence module of ContentForge AI.

Analyze the supplied source material. If an image is present, inspect the ACTUAL
image carefully: read visible text, headings, labels, numbers, tables, charts,
logos, objects, people (only when relevant to the content), dates and overall
context. Perform OCR/visual understanding.

Return JSON with exactly these fields:
{
  "title": "...",
  "content_type": "article|report|announcement|poster|social_post|document|photo|chart|other",
  "summary": "...",
  "key_facts": ["..."],
  "entities": ["..."],
  "dates": ["..."],
  "numbers": ["..."],
  "key_messages": ["..."],
  "visual_findings": ["..."],
  "uncertainties": ["..."]
}

Rules:
- The image itself is the source, not its filename or dimensions.
- Do NOT say "no readable text" merely because OCR is difficult. First inspect the
  visual content and describe meaningful visual information when available.
- Do not invent facts. If something cannot be established, put it in uncertainties.
- Keep facts concise and useful for downstream content generation.
- Return VALID JSON ONLY.
"""

    user_content = [{
        "type": "text",
        "text": analysis_prompt + "\n\nSOURCE TEXT:\n" + source
    }]
    if image_data_url:
        user_content.append({
            "type": "image_url",
            "image_url": {"url": image_data_url}
        })

    analysis_response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        max_completion_tokens=3000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You extract reliable source facts for a downstream content engine."},
            {"role": "user", "content": user_content},
        ],
    )
    source_brief = json.loads(analysis_response.choices[0].message.content)

    # ---------- Stage 2: transformation ----------
    output_schema = {}
    for key in outputs:
        if key == "linkedin":
            output_schema[key] = "object {title, hook, content, hashtags, source_basis}"
        elif key == "x":
            output_schema[key] = "object {title, posts: array of strings, source_basis}"
        elif key == "advisory":
            output_schema[key] = "object {title, priority, situation, key_findings, impact, recommended_actions, source_basis}"
        elif key == "summary":
            output_schema[key] = "object {title, executive_summary, key_points, implications, recommended_next_steps}"
        elif key == "presentation":
            output_schema[key] = "object {title, slides: array of {title, bullets, speaker_notes}, source_basis}"
        elif key == "infographic":
            output_schema[key] = "object {title, headline, key_statements, sections: array of {label, points}, visual_direction, call_to_action}"
        elif key == "video":
            output_schema[key] = "object {title, duration, opening_hook, scenes: array of {scene, duration, visual, narration, on_screen_text}, narration, subtitles}"

    transform_prompt = f"""You are ContentForge AI's Transformation Engine.

Transform ONE verified source-intelligence brief into the requested communication
artefacts.

SOURCE INTELLIGENCE:
{json.dumps(source_brief, ensure_ascii=False, indent=2)}

GENERATION SETTINGS:
{json.dumps(settings, ensure_ascii=False)}

REQUESTED OUTPUTS:
{json.dumps({k: OUTPUT_NAMES.get(k, k) for k in outputs}, ensure_ascii=False)}

OUTPUT SCHEMAS:
{json.dumps(output_schema, ensure_ascii=False, indent=2)}

QUALITY RULES:
1. Use the source intelligence as the factual ground truth.
2. Never invent facts, statistics, dates, names, quotes, sources or claims.
3. Do not mention the uploaded filename or image dimensions unless they are
   genuinely relevant to the source.
4. Every output must be polished enough to show in a hackathon demo.
5. Match the selected audience, tone, language, detail, objective and style.
6. Make each format genuinely different:
   - LinkedIn: strong hook, useful body, concise CTA/hashtags.
   - X: short platform-ready posts, coherent thread.
   - Advisory: situation, impact, action-oriented recommendations.
   - Executive Summary: concise decision-maker briefing.
   - Presentation: meaningful slide sequence, not generic placeholders.
   - Infographic: short visual messages and layout direction.
   - Video: production-ready scenes, narration and on-screen text.
7. If the source is an image/poster, use its actual visible message and visual
   context rather than saying the image is merely an image.
8. Return VALID JSON ONLY with an object named "outputs".
"""

    transform_response = client.chat.completions.create(
        model=model,
        temperature=0.6,
        max_completion_tokens=7000,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You are a senior editorial and communication transformation engine."},
            {"role": "user", "content": transform_prompt},
        ],
    )
    data = json.loads(transform_response.choices[0].message.content)
    return {
        "outputs": data.get("outputs", data),
        "_source_intelligence": source_brief,
    }


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
            generated = _groq_outputs(
                source_text, valid, settings, image_data_url=image_data_url
            )
            mode = "groq"
        except Exception as exc:
            generated = _demo_outputs(source_text, valid, settings)
            generated["_warning"] = (
                f"AI provider unavailable; demo mode used. Reason: {type(exc).__name__}: {exc}"
            )
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
        "outputs": generated.get("outputs", generated),
        "source_intelligence": generated.get("_source_intelligence"),
    }
