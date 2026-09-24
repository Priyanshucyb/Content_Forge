import os
import json
import re
from typing import Dict, List, Any, Optional
import requests

MAX_SOURCE_CHARS = int(os.getenv("MAX_SOURCE_CHARS", "50000"))
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

OUTPUT_NAMES = {
    "linkedin": "LinkedIn Post", "x": "X/Twitter Thread", "advisory": "Advisory",
    "summary": "Executive Summary", "presentation": "Presentation",
    "infographic": "Infographic", "video": "Video Package",
}


def _trim(text: str) -> str:
    return text[:MAX_SOURCE_CHARS]


def _demo_outputs(source: str, outputs: List[str], settings: Dict[str, str]) -> Dict[str, Any]:
    title = _make_title(source); facts = _extract_facts(source); bullets = facts[:5] or ["Key information extracted from the supplied source."]
    result = {}
    for key in outputs:
        if key == "linkedin": result[key] = {"title": title, "content": f"{title}\n\n{source[:900].strip()}\n\n#AI #Innovation #Technology", "source_basis": bullets}
        elif key == "x": result[key] = {"title": "X/Twitter Thread", "posts": [f"1/ {title}", f"2/ {bullets[0]}", f"3/ {bullets[1] if len(bullets)>1 else 'Key implications and actions.'}", "4/ Main takeaway: turn source information into clear, actionable communication."]}
        elif key == "advisory": result[key] = {"title": title, "sections": [{"heading":"Purpose","body":source[:700].strip()},{"heading":"Key Findings","body":"\n".join(f"• {x}" for x in bullets)},{"heading":"Recommended Actions","body":"• Review the source findings\n• Communicate relevant impacts\n• Track follow-up actions"}]}
        elif key == "summary": result[key] = {"title": title, "summary": source[:1500].strip(), "key_points": bullets, "implications": "Review the source in its operational context before decisions are taken."}
        elif key == "presentation": result[key] = {"title": title, "slides":[{"title":title,"bullets":[f"Audience: {settings['audience']}",f"Objective: {settings['objective']}"]},{"title":"Context","bullets":bullets[:3]},{"title":"Key Findings","bullets":bullets},{"title":"Implications","bullets":["What changes?","Who is affected?","What should happen next?"]},{"title":"Action Plan","bullets":["Prioritize key actions","Assign owners","Monitor outcomes"]}]}
        elif key == "infographic": result[key] = {"title":title,"headline":title,"sections":[{"label":"What happened?","points":bullets[:2]},{"label":"Why it matters","points":bullets[2:4] or ["Relevant implications"]},{"label":"What to do","points":["Review","Communicate","Act"]}]}
        elif key == "video": result[key] = {"title":title,"duration":"60–90 seconds","opening_hook":title,"narration":source[:1200].strip(),"scenes":[{"scene":1,"duration":"15s","visual":"Opening title and source context","narration":title,"on_screen_text":title},{"scene":2,"duration":"25s","visual":"Show key facts","narration":bullets[0],"on_screen_text":bullets[0]},{"scene":3,"duration":"20s","visual":"Show implications and actions","narration":"Focus on the practical takeaway and next steps.","on_screen_text":"Key takeaway"}]}
    return result


def _make_title(source: str) -> str:
    first = re.sub(r"\s+", " ", source.strip()).split(".")[0]
    return (first[:90] + "…") if len(first) > 90 else (first or "Source Content")


def _extract_facts(source: str) -> List[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", source) if len(s.strip()) > 30][:8]


def _groq_request(client_key: str, model: str, messages: list, max_tokens: int, json_mode: bool = False) -> str:
    payload = {"model": model, "messages": messages, "temperature": 0.2, "max_completion_tokens": max_tokens, "stream": False, "reasoning_effort": "none"}
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        r = requests.post(GROQ_URL, headers={"Authorization": f"Bearer {client_key}", "Content-Type": "application/json"}, json=payload, timeout=120)
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not reach Groq API: {exc}") from exc
    if not r.ok:
        try:
            detail = r.json().get("error", {}).get("message", r.text)
        except Exception:
            detail = r.text
        raise RuntimeError(f"Groq API {r.status_code}: {detail}")
    body = r.json()
    content = body.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        raise RuntimeError(f"Groq returned an empty response: {body}")
    return content


def _parse_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.I)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            try: return json.loads(text[start:end+1])
            except Exception: pass
        raise RuntimeError(f"Groq returned invalid JSON: {text[:500]}") from exc


def _groq_outputs(source: str, outputs: List[str], settings: Dict[str, str], image_data_url: Optional[str] = None) -> Dict[str, Any]:
    key = os.getenv("GROQ_API_KEY", "").strip()
    model = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b").strip()
    if not key: raise RuntimeError("GROQ_API_KEY is not configured on the backend.")

    # Stage 1: multimodal source intelligence. Metadata is explicitly separated from content.
    analysis_prompt = """You are ContentForge AI's Source Intelligence engine. Analyze the actual source.
If an image is attached, inspect the pixels carefully and perform visual understanding/OCR: read visible headings, paragraphs, labels, numbers, dates, logos, charts, tables and other meaningful visual context. The image is the source of truth.
The accompanying source text may contain ONLY filename/dimensions metadata; never treat metadata as the image's content.
Do not invent anything. If text is unclear, describe only what is actually visible and put uncertainty in uncertainties.
Return ONLY valid JSON with exactly these fields:
{"title":"","content_type":"article|report|announcement|poster|social_post|document|photo|chart|other","summary":"","key_facts":[],"entities":[],"dates":[],"numbers":[],"key_messages":[],"visual_findings":[],"uncertainties":[]}"""
    content = [{"type":"text","text":analysis_prompt + "\n\nSOURCE METADATA/TEXT:\n" + _trim(source)}]
    if image_data_url: content.append({"type":"image_url","image_url":{"url":image_data_url}})
    raw_brief = _groq_request(key, model, [{"role":"user","content":content}], 3000, True)
    source_brief = _parse_json(raw_brief)

    # Stage 2: text-only transformation from the shared structured brief.
    schema = {}
    for k in outputs:
        schema[k] = {
            "linkedin":"{title, hook, content, hashtags, source_basis}",
            "x":"{title, posts[], source_basis}",
            "advisory":"{title, priority, situation, key_findings[], impact, recommended_actions[], source_basis}",
            "summary":"{title, executive_summary, key_points[], implications, recommended_next_steps[]}",
            "presentation":"{title, slides:[{title, bullets[], speaker_notes}], source_basis}",
            "infographic":"{title, headline, key_statements[], sections:[{label,points[]}], visual_direction, call_to_action}",
            "video":"{title, duration, opening_hook, scenes:[{scene,duration,visual,narration,on_screen_text}], narration, subtitles[]}",
        }[k]
    transform_prompt = f"""You are ContentForge AI's Transformation Engine.
Use the SOURCE INTELLIGENCE below as the only factual ground truth and create the requested artefacts.
Never invent facts, names, statistics, dates, quotes or claims. Never mention filename or dimensions unless genuinely relevant.
Make outputs specific to the actual source. Do not use generic placeholders such as 'What changes?' or 'Review the source' when source facts can support a concrete statement.
Settings: {json.dumps(settings, ensure_ascii=False)}
Requested schemas: {json.dumps(schema, ensure_ascii=False)}
SOURCE INTELLIGENCE:
{json.dumps(source_brief, ensure_ascii=False, indent=2)}
Return ONLY valid JSON with top-level object {{"outputs": {{...}}}}."""
    raw_outputs = _groq_request(key, model, [{"role":"user","content":transform_prompt}], 7000, True)
    data = _parse_json(raw_outputs)
    return {"outputs": data.get("outputs", data), "_source_intelligence": source_brief}


def generate_outputs(source_text: str, outputs: List[str], audience: str, tone: str, language: str, detail: str, objective: str, style: str, image_data_url: Optional[str] = None):
    valid = [x for x in outputs if x in OUTPUT_NAMES]
    if not valid: raise ValueError("Select at least one valid output type.")
    settings = {"audience":audience,"tone":tone,"language":language,"detail":detail,"objective":objective,"style":style}
    if os.getenv("GROQ_API_KEY"):
        generated = _groq_outputs(source_text, valid, settings, image_data_url=image_data_url)
        mode = "groq"
    else:
        generated = _demo_outputs(source_text, valid, settings)
        mode = "demo-no-api-key"
    return {"mode":mode,"source":{"chars":len(source_text),"preview":source_text[:700],"outputs_requested":valid},"outputs":generated.get("outputs",generated),"source_intelligence":generated.get("_source_intelligence")}
