import requests
import json
import os
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from .prompts import SYSTEM_PROMPT, build_user_prompt
from .parser import parse_llm_response, create_error_response
from .rate_limiter import llm_request_queue


DEFAULT_LLM_API_URL = "http://localhost:11434/api/chat"
OPENAI_CHAT_COMPLETIONS_PATH = "/chat/completions"
logger = logging.getLogger(__name__)


def _get_llm_api_url() -> str:
    api_url = os.getenv("LLM_API_URL")
    if api_url:
        return api_url

    base_url = os.getenv("LLM_API_BASE_URL") or os.getenv("OPENAI_BASE_URL")
    if base_url:
        return f"{base_url.rstrip('/')}{OPENAI_CHAT_COMPLETIONS_PATH}"

    return DEFAULT_LLM_API_URL


def _get_llm_api_format(url: str) -> str:
    configured = os.getenv("LLM_API_FORMAT", "auto").strip().lower()
    if configured in {"openai", "ollama"}:
        return configured
    return "openai" if url.rstrip("/").endswith(OPENAI_CHAT_COMPLETIONS_PATH) else "ollama"


def _get_headers(api_format: str) -> dict:
    headers = {"Content-Type": "application/json"}
    api_key = os.getenv("AI_PROXY_KEY")
    if api_key and api_format == "openai":
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _extract_response_text(response_data: dict, api_format: str) -> str:
    if api_format == "openai":
        choices = response_data.get("choices") or []
        if not choices:
            return ""
        return choices[0].get("message", {}).get("content", "").strip()

    return response_data.get("message", {}).get("content", "").strip()


def _run_single_check(
    template: str,
    document: str,
    check_type: str,
    model: str,
    url: str,
    api_format: str
) -> dict:
    user_prompt = build_user_prompt(template, document, check_type=check_type)
    
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "stream": False
    }
    
    try:
        llm_request_queue.wait_for_turn(model)
        response = requests.post(url, json=payload, headers=_get_headers(api_format), timeout=1800)
        if not response.ok:
            return {
                "check_type": check_type,
                "error": f"HTTP {response.status_code}: {response.text[:500]}",
                "data": None
            }
        
        response_data = response.json()
        response_text = _extract_response_text(response_data, api_format)
        
        if not response_text:
            return {"check_type": check_type, "error": "Пустой ответ", "data": None}
        
        parsed = parse_llm_response(response_text)
        return {"check_type": check_type, "error": None, "data": parsed}
        
    except Exception as e:
        logger.exception(
            "LLM check failed: check_type=%s model=%s api_format=%s url=%s",
            check_type,
            model,
            api_format,
            url,
        )
        return {"check_type": check_type, "error": str(e), "data": None}


def _merge_results(structure: dict, content: dict, formatting: dict) -> dict:
    all_errors = []
    scores = {"structure": 100, "content": 100, "formatting": 100}
    summaries = []
    
    for result in [structure, content, formatting]:
        check_type = result["check_type"]
        
        if result["error"]:
            all_errors.append({
                "section": "Общий документ",
                "error_type": "structural" if check_type == "structure" else ("content" if check_type == "content" else "formatting"),
                "description": f"Ошибка проверки {check_type}: {result['error']}",
                "severity": "high"
            })
            scores[check_type] = 50
            summaries.append(f"{check_type}: ошибка запроса")
        elif result["data"]:
            data = result["data"]
            if isinstance(data, dict) and "errors" in data:
                all_errors.extend(data["errors"])
                scores[check_type] = data.get("compliance_score", 100)
                summaries.append(f"{check_type}: {data.get('summary', 'OK')}")
            else:
                scores[check_type] = 0
                summaries.append(f"{check_type}: некорректный формат ответа")
        else:
            scores[check_type] = 0
            summaries.append(f"{check_type}: нет данных")
    
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_errors.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 4))
    
    fmt_summary = next((s for s in summaries if "formatting:" in s.lower()), "")
    if "не проверено" in fmt_summary.lower() or "нет данных" in fmt_summary.lower():
        final_score = round(scores["structure"] * 0.5 + scores["content"] * 0.5)
    else:
        final_score = round(
            scores["structure"] * 0.4 + 
            scores["content"] * 0.4 + 
            scores["formatting"] * 0.2
        )
    
    return {
        "errors": all_errors,
        "compliance_score": final_score,
        "summary": " | ".join(summaries)
    }


def compare_documents(template_content, document_content, model="gpt-oss:120b-cloud", parallel: bool = True):
    url = _get_llm_api_url()
    api_format = _get_llm_api_format(url)
    check_types = ["structure", "content", "formatting"]
    
    if parallel:
        results = {}
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_check = {
                executor.submit(
                    _run_single_check,
                    template_content,
                    document_content,
                    ct,
                    model,
                    url,
                    api_format
                ): ct
                for ct in check_types
            }
            for future in as_completed(future_to_check):
                result = future.result()
                results[result["check_type"]] = result
    else:
        results = {}
        for ct in check_types:
            results[ct] = _run_single_check(template_content, document_content, ct, model, url, api_format)
    
    return _merge_results(
        structure=results.get("structure", {"check_type": "structure", "error": "Не выполнено", "data": None}),
        content=results.get("content", {"check_type": "content", "error": "Не выполнено", "data": None}),
        formatting=results.get("formatting", {"check_type": "formatting", "error": "Не выполнено", "data": None})
    )
