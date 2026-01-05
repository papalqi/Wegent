# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

import logging
import re
import time
from typing import List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_db
from app.core import security
from app.models.kind import Kind
from app.models.user import User
from app.schemas.model import (
    ModelBulkCreateItem,
    ModelCreate,
    ModelDetail,
    ModelInDB,
    ModelListResponse,
    ModelUpdate,
    ProviderModelsRequest,
    ProviderModelsResponse,
    ProviderProbeCheck,
    ProviderProbeRequest,
    ProviderProbeResponse,
)
from app.services.adapters import public_model_service
from app.services.model_aggregation_service import ModelType, model_aggregation_service

router = APIRouter()
logger = logging.getLogger(__name__)

_DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
_OK_PUNCTUATION = " .,!?:;，。！？"


def _normalize_openai_base_url(base_url: Optional[str]) -> str:
    if not base_url:
        return _DEFAULT_OPENAI_BASE_URL
    normalized = base_url.strip().rstrip("/")
    if normalized.endswith("/v1"):
        return normalized
    return f"{normalized}/v1"


def _validate_http_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _merge_headers(api_key: str, custom_headers: Optional[dict]) -> dict[str, str]:
    headers: dict[str, str] = {"Accept": "application/json"}
    if isinstance(custom_headers, dict):
        for k, v in custom_headers.items():
            if isinstance(k, str) and isinstance(v, str):
                headers[k] = v
    if "Authorization" not in headers and api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _extract_text_content(content: object) -> Optional[str]:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for part in content:
            if isinstance(part, str):
                parts.append(part)
                continue
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        text = "".join(parts).strip()
        return text or None
    return None


def _extract_openai_chat_completions_text(payload: object) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first = choices[0]
    if not isinstance(first, dict):
        return None
    message = first.get("message")
    if not isinstance(message, dict):
        return None
    return _extract_text_content(message.get("content"))


def _extract_openai_responses_text(payload: object) -> Optional[str]:
    if not isinstance(payload, dict):
        return None
    output_text = payload.get("output_text")
    if isinstance(output_text, str) and output_text:
        return output_text
    output = payload.get("output")
    if not isinstance(output, list):
        return None
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get("type") in {"output_text", "text"} and isinstance(
                c.get("text"), str
            ):
                return c["text"]
    return None


def _is_ok_text(text: Optional[str]) -> bool:
    if not text:
        return False

    normalized = text.strip()
    if not normalized:
        return False

    quote_chars = "\"'“”‘’"
    if (
        len(normalized) >= 2
        and normalized[0] in quote_chars
        and normalized[-1] in quote_chars
    ):
        normalized = normalized[1:-1].strip()

    normalized = normalized.rstrip(_OK_PUNCTUATION).strip()
    return normalized.upper() == "OK"


def _truncate_preview(text: str, max_len: int = 160) -> str:
    sanitized = re.sub(r"\s+", " ", text).strip()
    if len(sanitized) <= max_len:
        return sanitized
    return f"{sanitized[:max_len]}…"


async def _request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    headers: dict[str, str],
    json_body: Optional[dict] = None,
) -> tuple[Optional[object], Optional[int], Optional[str]]:
    start = time.perf_counter()
    try:
        resp = await client.request(method, url, headers=headers, json=json_body)
        latency_ms = int((time.perf_counter() - start) * 1000)
        resp.raise_for_status()
        try:
            payload = resp.json()
        except ValueError:
            return None, latency_ms, "invalid_json"
        return payload, latency_ms, None
    except httpx.TimeoutException:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return None, latency_ms, "timeout"
    except httpx.HTTPStatusError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        status_code = getattr(e.response, "status_code", None)
        return None, latency_ms, f"http_status:{status_code}"
    except httpx.RequestError as e:
        latency_ms = int((time.perf_counter() - start) * 1000)
        return None, latency_ms, f"request_error:{type(e).__name__}"


@router.get("", response_model=ModelListResponse)
def list_models(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user),
):
    """
    Get Model list (paginated, active only)
    """
    skip = (page - 1) * limit
    items = public_model_service.get_models(
        db=db, skip=skip, limit=limit, current_user=current_user
    )
    total = public_model_service.count_active_models(db=db, current_user=current_user)

    return {"total": total, "items": items}


@router.get("/names")
def list_model_names(
    shell_type: str = Query(..., description="Shell type (Agno, ClaudeCode)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user),
):
    """
    Get all active model names (legacy API, use /unified for new implementations)

    Response:
    {
      "data": [
        {"name": "string", "displayName": "string"}
      ]
    }
    """
    data = public_model_service.list_model_names(
        db=db, current_user=current_user, shell_type=shell_type
    )
    return {"data": data}


@router.get("/unified")
def list_unified_models(
    shell_type: Optional[str] = Query(
        None, description="Shell type to filter compatible models (Agno, ClaudeCode)"
    ),
    include_config: bool = Query(
        False, description="Whether to include full config in response"
    ),
    scope: str = Query(
        "personal",
        description="Query scope: 'personal' (default), 'group', or 'all'",
    ),
    group_name: Optional[str] = Query(
        None, description="Group name (required when scope='group')"
    ),
    model_category_type: Optional[str] = Query(
        None,
        description="Filter by model category type (llm, tts, stt, embedding, rerank)",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user),
):
    """
    Get unified list of all available models (both public and user-defined) with scope support.

    This endpoint aggregates models from:
    - Public models (type='public'): Shared across all users
    - User-defined models (type='user'): Private to the current user or group

    Scope behavior:
    - scope='personal' (default): personal models + public models
    - scope='group': group models + public models (requires group_name)
    - scope='all': personal + public + all user's groups

    Each model includes a 'type' field to identify its source, which is
    important for avoiding naming conflicts when binding models.

    Parameters:
    - shell_type: Optional shell type to filter compatible models
    - include_config: Whether to include full model config in response
    - scope: Query scope ('personal', 'group', or 'all')
    - group_name: Group name (required when scope='group')
    - model_category_type: Optional filter by model category type (llm, tts, stt, embedding, rerank)

    Response:
    {
      "data": [
        {
          "name": "model-name",
          "type": "public" | "user",
          "displayName": "Human Readable Name",
          "provider": "openai" | "claude",
          "modelId": "gpt-4",
          "modelCategoryType": "llm" | "tts" | "stt" | "embedding" | "rerank"
        }
      ]
    }
    """
    data = model_aggregation_service.list_available_models(
        db=db,
        current_user=current_user,
        shell_type=shell_type,
        include_config=include_config,
        scope=scope,
        group_name=group_name,
        model_category_type=model_category_type,
    )
    return {"data": data}


@router.get("/unified/{model_name}")
def get_unified_model(
    model_name: str,
    model_type: Optional[str] = Query(
        None, description="Model type ('public' or 'user')"
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(security.get_current_user),
):
    """
    Get a specific model by name, optionally with type hint.

    If model_type is not provided, it will try to find the model
    in the following order:
    1. User's own models (type='user')
    2. Public models (type='public')

    Parameters:
    - model_name: Model name
    - model_type: Optional model type hint ('public' or 'user')

    Response:
    {
      "name": "model-name",
      "type": "public" | "user",
      "displayName": "Human Readable Name",
      "provider": "openai" | "claude",
      "modelId": "gpt-4",
      "config": {...},
      "isActive": true
    }
    """
    from fastapi import HTTPException

    result = model_aggregation_service.resolve_model(
        db=db, current_user=current_user, name=model_name, model_type=model_type
    )

    if not result:
        raise HTTPException(status_code=404, detail="Model not found")

    return result


@router.post("", response_model=ModelInDB, status_code=status.HTTP_201_CREATED)
def create_model(
    model_create: ModelCreate,
    group_name: Optional[str] = Query(None, description="Group name (namespace)"),
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create new Model.

    If group_name is provided, creates the model in that group's namespace.
    User must have Developer+ permission in the group.
    Otherwise, creates a personal model in 'default' namespace.
    """
    return public_model_service.create_model(
        db=db, obj_in=model_create, current_user=current_user
    )


@router.post("/batch", status_code=status.HTTP_201_CREATED)
def bulk_create_models(
    items: List[ModelBulkCreateItem],
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Bulk upsert Models (create if not exists, update if exists).

    Request body example:
    [
      {
        "name": "modelname",
        "env": {
          "model": "xx",
          "base_url": "xx",
          "model_id": "xx",
          "api_key": "xx"
        }
      }
    ]

    Response:
    {
      "created": [ModelInDB...],
      "updated": [ModelInDB...],
      "skipped": [{"name": "...", "reason": "..."}]
    }
    """
    result = public_model_service.bulk_create_models(
        db=db, items=items, current_user=current_user
    )

    # Convert PublicModel objects to Model-like objects
    created = []
    for pm in result.get("created", []):
        model_data = {
            "id": pm.id,
            "name": pm.name,
            "config": pm.json.get("spec", {}).get("modelConfig", {}),
            "is_active": pm.is_active,
            "created_at": pm.created_at,
            "updated_at": pm.updated_at,
        }
        created.append(ModelInDB.model_validate(model_data))

    updated = []
    for pm in result.get("updated", []):
        model_data = {
            "id": pm.id,
            "name": pm.name,
            "config": pm.json.get("spec", {}).get("modelConfig", {}),
            "is_active": pm.is_active,
            "created_at": pm.created_at,
            "updated_at": pm.updated_at,
        }
        updated.append(ModelInDB.model_validate(model_data))

    return {
        "created": created,
        "updated": updated,
        "skipped": result.get("skipped", []),
    }


@router.get("/{model_id}", response_model=ModelDetail)
def get_model(
    model_id: int,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get specified Model details
    """
    return public_model_service.get_by_id(
        db=db, model_id=model_id, current_user=current_user
    )


@router.put("/{model_id}", response_model=ModelInDB)
def update_model(
    model_id: int,
    model_update: ModelUpdate,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update Model information
    """
    return public_model_service.update_model(
        db=db, model_id=model_id, obj_in=model_update, current_user=current_user
    )


@router.delete("/{model_id}")
def delete_model(
    model_id: int,
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete Model (set is_active to False)
    """
    public_model_service.delete_model(
        db=db, model_id=model_id, current_user=current_user
    )
    return {"message": "Model deleted successfully"}


@router.post("/test-connection")
def test_model_connection(
    test_data: dict,
    current_user: User = Depends(security.get_current_user),
):
    """
    Test model connection

    Request body:
    {
      "provider_type": "openai" | "anthropic" | "gemini",
      "model_id": "gpt-4",
      "api_key": "sk-...",
      "base_url": "https://api.openai.com/v1",  // optional
      "custom_headers": {"header-name": "header-value"},  // optional, custom HTTP headers
      "model_category_type": "llm" | "embedding" | "tts" | "stt" | "rerank"  // optional, defaults to "llm"
    }

    Response:
    {
      "success": true | false,
      "message": "Connection successful" | "Error message"
    }
    """
    provider_type = test_data.get("provider_type")
    model_id = test_data.get("model_id")
    api_key = test_data.get("api_key")
    base_url = test_data.get("base_url")
    custom_headers = test_data.get("custom_headers", {})
    model_category_type = test_data.get("model_category_type", "llm")

    if not provider_type or not model_id or not api_key:
        return {
            "success": False,
            "message": "Missing required fields: provider_type, model_id, api_key",
        }

    # Ensure custom_headers is a dict
    if not isinstance(custom_headers, dict):
        custom_headers = {}

    try:
        return _test_llm_connection(
            provider_type=provider_type,
            model_id=model_id,
            api_key=api_key,
            base_url=base_url,
            custom_headers=custom_headers,
            model_category_type=model_category_type,
        )

    except Exception as e:
        logger.error(f"Model connection test failed: {str(e)}")
        return {"success": False, "message": f"Connection failed: {str(e)}"}


@router.post("/provider-models", response_model=ProviderModelsResponse)
async def list_provider_models(
    req: ProviderModelsRequest,
    current_user: User = Depends(security.get_current_user),
):
    """
    Proxy provider /models endpoint to list upstream model IDs.

    Notes:
    - This endpoint intentionally runs on the backend to avoid CORS and API key leakage.
    - Currently supported providers: openai, openai-responses (OpenAI-compatible).
    """
    provider_type = (req.provider_type or "").strip()
    if provider_type not in {"openai", "openai-responses"}:
        return ProviderModelsResponse(
            success=False,
            message=f"Unsupported provider_type: {provider_type}",
            model_ids=[],
        )

    base_url_resolved = _normalize_openai_base_url(req.base_url)
    if not _validate_http_url(base_url_resolved):
        return ProviderModelsResponse(
            success=False,
            message="Invalid base_url",
            base_url_resolved=base_url_resolved,
            model_ids=[],
        )

    headers = _merge_headers(req.api_key, req.custom_headers)
    url = f"{base_url_resolved}/models"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            payload = resp.json()

        data = payload.get("data", []) if isinstance(payload, dict) else []
        model_ids: list[str] = []
        for item in data if isinstance(data, list) else []:
            if isinstance(item, dict):
                model_id = item.get("id") or item.get("name")
                if isinstance(model_id, str) and model_id:
                    model_ids.append(model_id)

        unique_model_ids = sorted(set(model_ids))
        return ProviderModelsResponse(
            success=True,
            message="OK",
            base_url_resolved=base_url_resolved,
            model_ids=unique_model_ids,
        )
    except httpx.TimeoutException:
        return ProviderModelsResponse(
            success=False,
            message="Request timed out",
            base_url_resolved=base_url_resolved,
            model_ids=[],
        )
    except httpx.HTTPStatusError as e:
        status_code = getattr(e.response, "status_code", None)
        return ProviderModelsResponse(
            success=False,
            message=f"Upstream returned HTTP {status_code}",
            base_url_resolved=base_url_resolved,
            model_ids=[],
        )
    except httpx.RequestError as e:
        return ProviderModelsResponse(
            success=False,
            message=f"Upstream request failed: {type(e).__name__}",
            base_url_resolved=base_url_resolved,
            model_ids=[],
        )


@router.post("/provider-probe", response_model=ProviderProbeResponse)
async def probe_provider(
    req: ProviderProbeRequest,
    current_user: User = Depends(security.get_current_user),
):
    """
    Perform a structured provider probe using real upstream requests.

    Supported checks (probe_targets):
    - list_models: GET /models
    - prompt_llm: POST /chat/completions (openai) or POST /responses (openai-responses)
    - embedding: POST /embeddings
    """
    provider_type = (req.provider_type or "").strip()
    probe_targets = req.probe_targets or ["list_models", "prompt_llm", "embedding"]

    checks: dict[str, ProviderProbeCheck] = {}

    if provider_type not in {"openai", "openai-responses"}:
        for target in probe_targets:
            checks[target] = ProviderProbeCheck(ok=False, error="unsupported_provider")
        return ProviderProbeResponse(
            success=False,
            message=f"Unsupported provider_type: {provider_type}",
            base_url_resolved=req.base_url,
            checks=checks,
        )

    base_url_resolved = _normalize_openai_base_url(req.base_url)
    if not _validate_http_url(base_url_resolved):
        for target in probe_targets:
            checks[target] = ProviderProbeCheck(ok=False, error="invalid_base_url")
        return ProviderProbeResponse(
            success=False,
            message="Invalid base_url",
            base_url_resolved=base_url_resolved,
            checks=checks,
        )

    headers = _merge_headers(req.api_key, req.custom_headers)

    async with httpx.AsyncClient(timeout=10.0) as client:
        if "list_models" in probe_targets:
            _payload, latency_ms, err = await _request_json(
                client, "GET", f"{base_url_resolved}/models", headers
            )
            checks["list_models"] = ProviderProbeCheck(
                ok=err is None, latency_ms=latency_ms, error=err
            )

        if "prompt_llm" in probe_targets:
            if not req.model_id:
                checks["prompt_llm"] = ProviderProbeCheck(
                    ok=False, error="model_id_required"
                )
            else:
                if provider_type == "openai-responses":
                    url = f"{base_url_resolved}/responses"
                    body = {
                        "model": req.model_id,
                        "input": "Reply with exactly OK. Ping.",
                        "max_output_tokens": 8,
                        "temperature": 0,
                    }
                    payload, latency_ms, err = await _request_json(
                        client, "POST", url, headers, json_body=body
                    )
                    text = _extract_openai_responses_text(payload)
                else:
                    url = f"{base_url_resolved}/chat/completions"
                    body = {
                        "model": req.model_id,
                        "messages": [
                            {"role": "system", "content": "Reply with exactly OK."},
                            {"role": "user", "content": "Ping."},
                        ],
                        "temperature": 0,
                        "max_tokens": 8,
                    }
                    payload, latency_ms, err = await _request_json(
                        client, "POST", url, headers, json_body=body
                    )
                    text = _extract_openai_chat_completions_text(payload)

                if err is None and not _is_ok_text(text):
                    if text is None:
                        err = "unexpected_response:no_text"
                    else:
                        err = f"unexpected_response:text={_truncate_preview(text)}"
                checks["prompt_llm"] = ProviderProbeCheck(
                    ok=err is None, latency_ms=latency_ms, error=err
                )

        if "embedding" in probe_targets:
            if not req.model_id:
                checks["embedding"] = ProviderProbeCheck(
                    ok=False, error="model_id_required"
                )
            else:
                url = f"{base_url_resolved}/embeddings"
                body = {"model": req.model_id, "input": "test"}
                payload, latency_ms, err = await _request_json(
                    client, "POST", url, headers, json_body=body
                )
                if err is None:
                    try:
                        data = (
                            payload.get("data") if isinstance(payload, dict) else None
                        )
                        emb = (
                            data[0].get("embedding")
                            if isinstance(data, list)
                            and data
                            and isinstance(data[0], dict)
                            else None
                        )
                        if not isinstance(emb, list) or not emb:
                            err = "unexpected_response:missing_embedding"
                    except Exception:
                        err = "unexpected_response:missing_embedding"

                checks["embedding"] = ProviderProbeCheck(
                    ok=err is None, latency_ms=latency_ms, error=err
                )

    success = bool(checks) and all(c.ok for c in checks.values())
    return ProviderProbeResponse(
        success=success,
        message="OK" if success else "Probe failed",
        base_url_resolved=base_url_resolved,
        checks=checks,
    )


def _test_llm_connection(
    provider_type: str,
    model_id: str,
    api_key: str,
    base_url: Optional[str],
    custom_headers: dict,
    model_category_type: str,
) -> dict:
    """Test LLM API connection using LangChain.

    Supports OpenAI, OpenAI Responses API, Anthropic, and Gemini providers.

    Args:
        provider_type: Provider type (openai, openai-responses, anthropic, gemini)
        model_id: The model ID to test
        api_key: API key for the provider
        base_url: Optional base URL for the API
        custom_headers: Optional custom HTTP headers
        model_category_type: Type of model (llm, embedding, tts, stt, rerank)
    """
    # Handle non-LLM model types
    if model_category_type == "embedding":
        return _test_embedding_connection(
            provider_type, model_id, api_key, base_url, custom_headers
        )
    elif model_category_type == "tts":
        return {
            "success": True,
            "message": f"TTS model {model_id} configured. Audio synthesis test requires actual audio output.",
        }
    elif model_category_type == "stt":
        return {
            "success": True,
            "message": f"STT model {model_id} configured. Audio transcription test requires actual audio input.",
        }
    elif model_category_type == "rerank":
        return {
            "success": True,
            "message": f"Rerank model {model_id} configured. Please verify with actual rerank request.",
        }

    # LLM test using LangChain
    if provider_type == "openai":
        from langchain_openai import ChatOpenAI

        chat_kwargs = {
            "model": model_id,
            "api_key": api_key,
            "max_tokens": 128,
        }
        if base_url:
            chat_kwargs["base_url"] = base_url
        if custom_headers:
            chat_kwargs["default_headers"] = custom_headers

        chat = ChatOpenAI(**chat_kwargs)
        chat.invoke("hi")
        return {
            "success": True,
            "message": f"Successfully connected to {model_id} using Chat Completions API",
        }

    elif provider_type == "openai-responses":
        from langchain_openai import ChatOpenAI

        chat_kwargs = {
            "model": model_id,
            "api_key": api_key,
            "max_tokens": 128,
            "use_responses_api": True,
        }
        if base_url:
            chat_kwargs["base_url"] = base_url
        if custom_headers:
            chat_kwargs["default_headers"] = custom_headers

        chat = ChatOpenAI(**chat_kwargs)
        chat.invoke("hi")
        return {
            "success": True,
            "message": f"Successfully connected to {model_id} using Responses API",
        }

    elif provider_type == "anthropic":
        from langchain_anthropic import ChatAnthropic

        chat_kwargs = {
            "model": model_id,
            "api_key": api_key,
            "max_tokens": 128,
        }
        if base_url:
            chat_kwargs["base_url"] = base_url
        if custom_headers:
            chat_kwargs["default_headers"] = custom_headers

        chat = ChatAnthropic(**chat_kwargs)
        chat.invoke("hi")
        return {
            "success": True,
            "message": f"Successfully connected to {model_id}",
        }

    elif provider_type == "gemini":
        from langchain_google_genai import ChatGoogleGenerativeAI

        chat_kwargs = {
            "model": model_id,
            "google_api_key": api_key,
            "max_output_tokens": 128,
        }
        # Note: ChatGoogleGenerativeAI doesn't support custom base_url or headers directly
        # For custom endpoints, users should use environment variables

        chat = ChatGoogleGenerativeAI(**chat_kwargs)
        chat.invoke("hi")
        return {
            "success": True,
            "message": f"Successfully connected to {model_id}",
        }

    else:
        return {
            "success": False,
            "message": f"Unsupported provider type: {provider_type}",
        }


def _test_embedding_connection(
    provider_type: str,
    model_id: str,
    api_key: str,
    base_url: Optional[str],
    custom_headers: dict,
) -> dict:
    """Test embedding model connection using LangChain."""
    if provider_type in ["openai", "openai-responses"]:
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(
            model=model_id,
            api_key=api_key,
            base_url=base_url or "https://api.openai.com/v1",
            default_headers=custom_headers if custom_headers else None,
        )
        embeddings.embed_query("test")
        return {
            "success": True,
            "message": f"Successfully connected to embedding model {model_id}",
        }

    elif provider_type == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embeddings = GoogleGenerativeAIEmbeddings(
            model=model_id,
            google_api_key=api_key,
        )
        embeddings.embed_query("test")
        return {
            "success": True,
            "message": f"Successfully connected to embedding model {model_id}",
        }

    else:
        return {
            "success": False,
            "message": f"Embedding not supported for provider: {provider_type}",
        }


@router.get("/compatible")
def get_compatible_models(
    shell_type: str = Query(..., description="Shell type (Agno or ClaudeCode)"),
    current_user: User = Depends(security.get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get models compatible with a specific shell type

    Parameters:
    - shell_type: "Agno" or "ClaudeCode"

    Response:
    {
      "models": [
        {"name": "my-gpt4-model"},
        {"name": "my-gpt4o-model"}
      ]
    }
    """
    from app.schemas.kind import Model as ModelCRD

    # Query all active Model CRDs from kinds table
    models = (
        db.query(Kind)
        .filter(
            Kind.user_id == current_user.id,
            Kind.kind == "Model",
            Kind.namespace == "default",
            Kind.is_active == True,
        )
        .all()
    )

    compatible_models = []

    for model_kind in models:
        try:
            if not model_kind.json:
                continue
            model_crd = ModelCRD.model_validate(model_kind.json)
            model_config = model_crd.spec.modelConfig
            if isinstance(model_config, dict):
                env = model_config.get("env", {})
                model_type = env.get("model", "")

                # Filter compatible models
                # Agno supports OpenAI, Claude and Gemini models
                if shell_type == "Agno" and model_type in [
                    "openai",
                    "claude",
                    "gemini",
                ]:
                    compatible_models.append({"name": model_kind.name})
                elif shell_type == "ClaudeCode" and model_type == "claude":
                    compatible_models.append({"name": model_kind.name})
        except Exception as e:
            logger.warning(f"Failed to parse model {model_kind.name}: {e}")
            continue

    return {"models": compatible_models}
