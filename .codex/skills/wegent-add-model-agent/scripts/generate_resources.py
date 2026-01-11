#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def _parse_bind_mode(value: str) -> list[str]:
    items = [part.strip() for part in value.split(",")]
    return [item for item in items if item]


def _default_bind_mode(shell_name: str) -> list[str]:
    if shell_name in {"Chat", "Dify"}:
        return ["chat"]
    return ["code"]


def _build_resources(args: argparse.Namespace) -> list[dict[str, Any]]:
    if bool(args.api_key) and bool(args.api_key_env):
        raise ValueError("Only one of --api-key or --api-key-env can be set.")

    api_key_value = ""
    if args.api_key_env:
        api_key_value = f"${{{args.api_key_env}}}"
    elif args.api_key:
        api_key_value = args.api_key

    if not api_key_value:
        # Avoid printing secrets; only warn about emptiness.
        print(
            "Warning: api_key is empty. The model will not work until you set "
            "--api-key or --api-key-env (recommended).",
            file=sys.stderr,
        )

    env: dict[str, Any] = {
        "model": args.provider,
        "model_id": args.model_id,
        "api_key": api_key_value,
    }
    if args.base_url:
        env["base_url"] = args.base_url

    model_spec: dict[str, Any] = {
        "modelConfig": {"env": env},
        "isCustomConfig": True,
    }
    if args.protocol:
        model_spec["protocol"] = args.protocol
    else:
        model_spec["protocol"] = args.provider
    if args.api_format:
        model_spec["apiFormat"] = args.api_format

    resources: list[dict[str, Any]] = [
        {
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Model",
            "metadata": {"name": args.model_name, "namespace": args.namespace},
            "spec": model_spec,
            "status": {"state": "Available"},
        },
        {
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Ghost",
            "metadata": {"name": args.ghost_name, "namespace": args.namespace},
            "spec": {
                "systemPrompt": args.system_prompt,
                "mcpServers": {},
                "skills": [],
            },
            "status": {"state": "Available"},
        },
        {
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Bot",
            "metadata": {"name": args.bot_name, "namespace": args.namespace},
            "spec": {
                "ghostRef": {"name": args.ghost_name, "namespace": args.namespace},
                "shellRef": {"name": args.shell_name, "namespace": "default"},
                "modelRef": {"name": args.model_name, "namespace": args.namespace},
            },
            "status": {"state": "Available"},
        },
        {
            "apiVersion": "agent.wecode.io/v1",
            "kind": "Team",
            "metadata": {"name": args.team_name, "namespace": args.namespace},
            "spec": {
                "description": args.team_description,
                "members": [
                    {
                        "role": "leader",
                        "botRef": {"name": args.bot_name, "namespace": args.namespace},
                        "prompt": "",
                    }
                ],
                "collaborationModel": args.collaboration_model,
                "bind_mode": args.bind_mode,
            },
            "status": {"state": "Available"},
        },
    ]

    return resources


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Wegent resource bundle (Model/Ghost/Bot/Team) as a JSON array. "
            "The output can be applied via `wegent apply -f <file> -n <namespace>`."
        )
    )
    parser.add_argument("--namespace", default="default", help="Resource namespace")

    parser.add_argument("--team-name", required=True, help="Team name")
    parser.add_argument(
        "--team-description", default="", help="Optional team description"
    )
    parser.add_argument(
        "--collaboration-model",
        default="solo",
        help="Team collaboration model (e.g., solo, pipeline, route, coordinate, collaborate)",
    )

    parser.add_argument("--model-name", required=True, help="Model resource name")
    parser.add_argument(
        "--provider",
        default="openai",
        help="Model provider type (e.g., openai, claude, gemini)",
    )
    parser.add_argument("--model-id", required=True, help="Provider model ID")
    parser.add_argument(
        "--base-url",
        default="",
        help="Optional base URL (e.g., https://api.openai.com/v1)",
    )
    parser.add_argument(
        "--api-key",
        default="",
        help="API key (discouraged; prefer --api-key-env to avoid leaking secrets)",
    )
    parser.add_argument(
        "--api-key-env",
        default="",
        help="Environment variable name to reference as ${ENV_VAR} in api_key",
    )
    parser.add_argument(
        "--api-format",
        default="",
        help="Optional OpenAI API format (responses or chat/completions)",
    )
    parser.add_argument(
        "--protocol",
        default="",
        help="Optional Model.spec.protocol (defaults to --provider)",
    )

    parser.add_argument(
        "--shell-name",
        default="Chat",
        help="Shell name to reference (default: Chat; must exist as a public shell)",
    )

    parser.add_argument(
        "--ghost-name",
        default="",
        help="Ghost resource name (default: <team-name>-ghost)",
    )
    parser.add_argument(
        "--bot-name",
        default="",
        help="Bot resource name (default: <team-name>-bot)",
    )
    parser.add_argument(
        "--system-prompt",
        default="You are a helpful assistant.",
        help="Ghost system prompt",
    )

    parser.add_argument(
        "--bind-mode",
        default="",
        help="Comma-separated bind modes (e.g., chat,code). Defaults based on --shell-name.",
    )

    parser.add_argument(
        "--out",
        default="",
        help="Output file path (writes JSON array). If omitted, print to stdout.",
    )

    args = parser.parse_args()

    if not args.ghost_name:
        args.ghost_name = f"{args.team_name}-ghost"
    if not args.bot_name:
        args.bot_name = f"{args.team_name}-bot"

    if args.bind_mode:
        args.bind_mode = _parse_bind_mode(args.bind_mode)
    else:
        args.bind_mode = _default_bind_mode(args.shell_name)

    # Normalize empty strings to None where appropriate
    if not args.api_format:
        args.api_format = None

    resources = _build_resources(args)
    payload = json.dumps(resources, indent=2, ensure_ascii=False)

    if args.out:
        out_path = Path(args.out)
        out_path.write_text(payload + "\n", encoding="utf-8")
        print(str(out_path))
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
