#!/usr/bin/env python

# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-

from __future__ import annotations

import io
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.logger import setup_logger

logger = setup_logger("skill_deployer")


def deploy_skills_from_backend(
    *,
    task_data: Dict[str, Any],
    skills: List[str],
    skills_dir: str,
    namespace: str = "default",
    clear_existing: bool = True,
) -> int:
    """
    Download Skills from Backend API and deploy them to `skills_dir`.

    Uses `/api/v1/kinds/skills/unified` first to support both user skills and public
    skills (user_id=0) created from `backend/init_data/skills/`.
    """
    skills = [s.strip() for s in (skills or []) if isinstance(s, str) and s.strip()]
    if not skills:
        return 0

    auth_token = task_data.get("auth_token")
    if not auth_token:
        logger.warning("No auth token available, cannot download skills")
        return 0

    api_base_url = os.getenv("TASK_API_DOMAIN", "http://wegent-backend:8000").rstrip(
        "/"
    )
    headers = {"Authorization": f"Bearer {auth_token}"}

    target_dir = os.path.expanduser(skills_dir)
    if clear_existing and os.path.exists(target_dir):
        shutil.rmtree(target_dir)
        logger.info("Cleared existing skills directory: %s", target_dir)
    Path(target_dir).mkdir(parents=True, exist_ok=True)

    try:
        import requests
    except Exception as e:
        logger.error("Requests not available for skill download: %s", e)
        return 0

    skill_index: Dict[str, Tuple[Optional[str], bool]] = {}
    try:
        unified_url = (
            f"{api_base_url}/api/v1/kinds/skills/unified"
            f"?skip=0&limit=1000&namespace={namespace}"
        )
        unified_response = requests.get(unified_url, headers=headers, timeout=30)
        if unified_response.status_code == 200:
            unified_data = unified_response.json()
            if isinstance(unified_data, list):
                for item in unified_data:
                    if not isinstance(item, dict):
                        continue
                    name = item.get("name")
                    skill_id = item.get("id")
                    if not name or skill_id is None:
                        continue
                    skill_index[name] = (str(skill_id), bool(item.get("is_public")))
                logger.info("Loaded unified skills index: count=%s", len(skill_index))
            else:
                logger.warning(
                    "Unexpected unified skills response type: %s", type(unified_data)
                )
        else:
            logger.warning(
                "Failed to fetch unified skills list: HTTP %s",
                unified_response.status_code,
            )
    except Exception as e:
        logger.warning("Failed to fetch unified skills list: %s", e)

    def _is_zip_member_safe(name: str) -> bool:
        # Prevent Zip Slip; allow only relative paths without parent traversal.
        path = Path(name)
        if path.is_absolute():
            return False
        return ".." not in path.parts

    success_count = 0
    for skill_name in skills:
        try:
            skill_id: Optional[str] = None
            is_public = False

            indexed = skill_index.get(skill_name)
            if indexed:
                skill_id, is_public = indexed

            # Fallback: query user skills by name (older backend compatibility)
            if not skill_id:
                list_url = f"{api_base_url}/api/v1/kinds/skills?name={skill_name}"
                response = requests.get(list_url, headers=headers, timeout=30)
                if response.status_code != 200:
                    logger.error(
                        "Failed to query skill '%s': HTTP %s",
                        skill_name,
                        response.status_code,
                    )
                    continue

                skills_data = response.json()
                skill_items = skills_data.get("items", [])
                if not skill_items:
                    logger.error("Skill '%s' not found", skill_name)
                    continue

                fallback_item = skill_items[0]
                skill_id = fallback_item.get("metadata", {}).get("labels", {}).get("id")
                is_public = False

            if not skill_id:
                logger.error("Skill '%s' has no ID", skill_name)
                continue

            if is_public:
                download_url = (
                    f"{api_base_url}/api/v1/kinds/skills/public/{skill_id}/download"
                )
            else:
                download_url = f"{api_base_url}/api/v1/kinds/skills/{skill_id}/download"

            response = requests.get(download_url, headers=headers, timeout=60)
            if response.status_code != 200:
                logger.error(
                    "Failed to download skill '%s': HTTP %s",
                    skill_name,
                    response.status_code,
                )
                continue

            with zipfile.ZipFile(io.BytesIO(response.content)) as zip_file:
                if not all(
                    _is_zip_member_safe(m.filename) for m in zip_file.infolist()
                ):
                    logger.error(
                        "Unsafe file path detected in skill ZIP: %s", skill_name
                    )
                    continue
                zip_file.extractall(target_dir)

            skill_target_dir = os.path.join(target_dir, skill_name)
            if os.path.isdir(skill_target_dir):
                logger.info("Deployed skill '%s' to %s", skill_name, skill_target_dir)
                success_count += 1
            else:
                logger.error("Skill folder '%s' not found after extraction", skill_name)

        except Exception as e:
            logger.warning("Failed to download skill '%s': %s", skill_name, e)
            continue

    if success_count:
        logger.info(
            "Successfully deployed %s/%s skills to %s",
            success_count,
            len(skills),
            target_dir,
        )
    else:
        logger.warning("No skills were successfully deployed")

    return success_count
