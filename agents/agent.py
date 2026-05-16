import json
import re 
from openai import OpenAI
from agents import retriever
from config import GROQ_API_KEY, MAX_TURNS, MODEL_NAME, GROQ_BASE_URL, INTENT_MAP
from agents.prompts import (GUARD_PROMPT, CLARIFICATION_PROMPT, RECOMMENDATION_PROMPT, COMPARISON_PROMPT, OUT_OF_SCOPE_REPLY, INTENT_EXTRACTION_PROMPT)
from agents.retriever import filter_retrieve, is_valid_url, by_name, TOTAL_CAT

client = OpenAI(base_url=GROQ_BASE_URL, api_key=GROQ_API_KEY)

def parse_json(text: str) -> dict:
    text = re.sub(r"```json|```", "", text).strip()
    start = text.find("{")
    end   = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON found in response")
    return json.loads(text[start:end])


def format_conversation(messages: list) -> str:
    lines = []
    for m in messages:
        role = "User" if m["role"] == "user" else "Assistant"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def format_catalog_items(items: list) -> str:
    lines = []
    for item in items:
        types = ", ".join(item.get("test_types", []))
        lines.append(
            f"Name: {item['name']}\n"
            f"URL: {item['url']}\n"
            f"Test Types: {types}\n"
            f"Description: {item.get('description', '')}\n"
            f"Job Levels: {', '.join(item.get('job_levels', []))}\n"
            f"Duration: {item.get('approx_duration', 'N/A')} minutes\n"
        )
    return "\n---\n".join(lines)

def build_response(reply: str, recommendations: list, end: bool) -> dict:
    valid_recs = []
    for r in recommendations:
        url = str(r.get("url", ""))
        if is_valid_url(url):
            valid_recs.append({
                "name":      str(r.get("name", "")),
                "url":       url,
                "test_type": str(r.get("test_type", ""))
            })
    return {
        "reply":               str(reply),
        "recommendations":     valid_recs[:10],
        "end_of_conversation": bool(end)
    }


def is_in_scope(message: str) -> bool:
    try:
        prompt = GUARD_PROMPT.format(message=message)
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1000,
            response_format={"type": "json_object"}
        )
        result = parse_json(resp.choices[0].message.content)
        return result.get("in_scope", True)
    except Exception as e:
        return True


# def fallback_intent(messages: list) -> dict:
    text     = " ".join(m["content"] for m in messages).lower()
    types    = []
    keywords = []
    for kw, mapped_types in INTENT_MAP.items():
        if kw in text:
            types.extend(mapped_types)
            keywords.append(kw)
    return {
        "role":           "",
        "keywords":       list(set(keywords)),
        "test_types":     list(set(types)),
        "level":          "any",
        "enough_context": bool(types)
    }


def extract_intent(messages: list) -> dict:
    try:
        conversation = format_conversation(messages)
        prompt = INTENT_EXTRACTION_PROMPT.format(conversation=conversation)
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=3000,
             response_format={"type": "json_object"}
        )
        return parse_json(resp.choices[0].message.content)
    except Exception as e:
        print(f"INTENT EXTRACTION ERROR: {e}")
        # return fallback_intent(messages) 


def clarify(messages: list, intent: dict) -> dict:
    try:
        conversation = format_conversation(messages)
        known = (
            f"Role: {intent.get('role', 'unknown')}, "
            f"Level: {intent.get('level', 'unknown')}, "
            f"Test types: {intent.get('test_types', [])}"
        )
        prompt = CLARIFICATION_PROMPT.format(
            conversation=conversation,
            known_context=known
        )
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=150,
        )
        reply = resp.choices[0].message.content.strip()
        return build_response(reply, [], False)
    except Exception:
        return build_response(
            "Could you tell me more about the role you are hiring for?",
            [], False
        )


def is_comparison_query(messages: list) -> list:
    last     = messages[-1]["content"].lower()
    triggers = ["compare", "difference between", "vs", "versus", "which is better"]
    if not any(t in last for t in triggers):
        return []
    mentioned = []
    for item in TOTAL_CAT:
        if item["name"].lower() in last:
            mentioned.append(item["name"])
    return mentioned


def compare(messages: list, names: list) -> dict:
    try:
        items = [by_name(n) for n in names]
        items = [i for i in items if i]
        if not items:
            return build_response(
                "I couldn't find those assessments in the catalog. Could you check the names?",
                [], False
            )
        conversation = format_conversation(messages)
        items_text   = format_catalog_items(items)
        prompt = COMPARISON_PROMPT.format(
            items_to_compare=items_text,
            conversation=conversation
        )
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
            response_format={"type": "json_object"}
        )
        result = parse_json(resp.choices[0].message.content)
        return build_response(result.get("reply", ""), [], False)
    except Exception as e:
        print(f"COMPARISON ERROR: {e}")
        return build_response(
            "I had trouble comparing those assessments. Please try again.",
            [], False
        )


def recommend(messages: list, candidates: list) -> dict:
    try:
        conversation = format_conversation(messages)
        catalog_text = format_catalog_items(candidates)
        prompt = RECOMMENDATION_PROMPT.format(
            catalog_items=catalog_text,
            conversation=conversation
        )
        resp = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )
        raw = resp.choices[0].message.content
        print(f"RAW RESPONSE: {repr(raw)}") 
        print(f"FINISH REASON: {resp.choices[0].finish_reason}") ## debug
        result = parse_json(raw)
        return build_response(
            result.get("reply", ""),
            result.get("recommendations", []),
            result.get("end_of_conversation", False)
        )
    except Exception as e:
        print(f"RECOMMEND ERROR: {e}")
        return build_response(
            "I had trouble generating recommendations. Please try again.",
            [], False
        )


def process_chat(messages: list) -> dict:
    if len(messages) > MAX_TURNS:
        return build_response(
            "We have reached the maximum conversation length. Please start a new conversation.",
            [], True
        )

    last_user_message = messages[-1]["content"]

    if not is_in_scope(last_user_message):
        return OUT_OF_SCOPE_REPLY

    names = is_comparison_query(messages)
    if names:
        return compare(messages, names)

    intent = extract_intent(messages)

    
    if len(messages) > 2:
        all_text = " ".join(m["content"] for m in messages).lower()
        if "personality" in all_text and "P" not in intent["test_types"]:
            intent["test_types"].append("P")
        if ("ability" in all_text or "aptitude" in all_text) and "A" not in intent["test_types"]:
            intent["test_types"].append("A")
        if ("simulation" in all_text or "simulate" in all_text) and "S" not in intent["test_types"]:
            intent["test_types"].append("S")
        if "competency" in all_text and "C" not in intent["test_types"]:
            intent["test_types"].append("C")

    if not intent.get("enough_context", False):
        return clarify(messages, intent)

    candidates = filter_retrieve(intent)
    print(f"INTENT: {intent}")
    print(f"CANDIDATES: {[c['name'] for c in candidates]}")
    return recommend(messages, candidates)