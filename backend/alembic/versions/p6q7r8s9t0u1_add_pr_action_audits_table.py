# SPDX-FileCopyrightText: 2025 Weibo, Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""
Add pr_action_audits table.

Revision ID: p6q7r8s9t0u1
Revises: o5p6q7r8s9t0
Create Date: 2026-01-02
"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "p6q7r8s9t0u1"
down_revision = "o5p6q7r8s9t0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "pr_action_audits",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False, index=True),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column(
            "provider", sa.String(length=32), nullable=False, server_default="github"
        ),
        sa.Column(
            "git_domain",
            sa.String(length=255),
            nullable=False,
            server_default="github.com",
        ),
        sa.Column("repo_full_name", sa.String(length=255), nullable=False),
        sa.Column("base_branch", sa.String(length=255), nullable=False),
        sa.Column("head_branch", sa.String(length=255), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("policy_code", sa.String(length=64), nullable=True),
        sa.Column("policy_message", sa.String(length=1024), nullable=True),
        sa.Column("request_json", sa.Text(), nullable=False),
        sa.Column("response_json", sa.Text(), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("pr_url", sa.String(length=1024), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint(
            "user_id", "idempotency_key", name="uq_pr_action_idempotency"
        ),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "ix_pr_action_audits_user_id",
        "pr_action_audits",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_pr_action_audits_created_at",
        "pr_action_audits",
        ["created_at"],
        unique=False,
    )


def downgrade():
    op.drop_index("ix_pr_action_audits_created_at", table_name="pr_action_audits")
    op.drop_index("ix_pr_action_audits_user_id", table_name="pr_action_audits")
    op.drop_table("pr_action_audits")
