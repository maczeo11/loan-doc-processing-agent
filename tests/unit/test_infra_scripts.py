"""
Unit tests for Phase 7: AWS deployment and operations automation scripts.
Validates script presence, syntax standards, IAM least-privilege policies,
Caddy production configuration, and version-stamped API health endpoint.
"""

import os
import json
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

INFRA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../infra"))

EXPECTED_SCRIPTS = [
    "aws_setup.sh",
    "ec2_setup.sh",
    "version.sh",
    "deploy.sh",
    "rollback.sh",
    "stop.sh",
    "start.sh",
    "teardown.sh",
]


def test_scripts_exist_and_have_safe_shebang():
    """Verify all required scripts exist, have bash shebang, and enable strict mode."""
    for script_name in EXPECTED_SCRIPTS:
        script_path = os.path.join(INFRA_DIR, script_name)
        assert os.path.exists(script_path), f"Missing script: {script_path}"
        content = open(script_path, "r", encoding="utf-8").read()
        assert content.startswith("#!/usr/bin/env bash"), f"{script_name} missing bash shebang"
        assert "set -euo pipefail" in content, f"{script_name} missing strict mode 'set -euo pipefail'"


def test_iam_policy_structure_and_least_privilege():
    """Verify IAM policy is valid JSON and strictly scoped to FinScan resources without wildcards."""
    policy_path = os.path.join(INFRA_DIR, "iam_policy.json")
    assert os.path.exists(policy_path), f"Missing IAM policy: {policy_path}"

    with open(policy_path, "r", encoding="utf-8") as f:
        policy = json.load(f)

    assert policy.get("Version") == "2012-10-17"
    statements = policy.get("Statement", [])
    assert len(statements) >= 3, "IAM policy must have at least 3 statements (S3 bucket, S3 objects, SQS)"

    # Verify every statement has explicit non-wildcard resource scoping,
    # except Textract DetectDocumentText: AWS offers no resource-level
    # permission for it, so Resource "*" is mandatory (not a privilege widen).
    # That statement must contain ONLY textract actions.
    for stmt in statements:
        assert stmt.get("Effect") == "Allow"
        actions = stmt.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        resources = stmt.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]
        if all(a.startswith("textract:") for a in actions):
            assert resources == ["*"], "Textract statement must use bare Resource '*' (no ARNs exist for it)"
            continue
        for res in resources:
            assert res != "*", "Wildcard '*' account-wide resource is forbidden in least-privilege policy"
            assert ("${BUCKET_NAME}" in res or "${QUEUE_NAME}" in res or "${DLQ_NAME}" in res), (
                f"Resource {res} does not reference scoped FinScan placeholder variables"
            )


def test_caddy_production_config():
    """Verify Caddyfile.production has HTTPS proxy, security headers, and domain variable."""
    caddy_path = os.path.join(INFRA_DIR, "Caddyfile.production")
    assert os.path.exists(caddy_path), f"Missing Caddy production file: {caddy_path}"
    content = open(caddy_path, "r", encoding="utf-8").read()

    assert "{$DOMAIN_NAME:localhost}" in content
    # Systemd-native deploy model: api runs on the host, not a Docker network
    # alias - Caddy (network_mode: host) reaches it via loopback.
    assert "reverse_proxy 127.0.0.1:8000" in content
    assert "Strict-Transport-Security" in content
    assert "header_up X-Forwarded-Proto {scheme}" in content
    # Ensure database/Redis are not exposed in Caddy
    assert "5432" not in content
    assert "6379" not in content


def test_api_health_version_metadata():
    """Verify API /health exposes version, git SHA, and build timestamp without secrets."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "ok"
    assert data["service"] == "finscan-api"
    assert "version" in data
    assert "git_sha" in data
    assert "build_timestamp" in data
    assert "environment" in data
    # Verify no secret credentials leaked
    assert "SECRET" not in str(data)
    assert "KEY" not in str(data)


def test_teardown_safety_guards():
    """Verify teardown.sh defaults to dry-run and requires --confirm flag."""
    teardown_path = os.path.join(INFRA_DIR, "teardown.sh")
    content = open(teardown_path, "r", encoding="utf-8").read()

    assert "--confirm" in content
    assert "DRY_RUN=1" in content
    assert "PROJECT_PREFIX" in content


def test_deploy_rollback_safety():
    """Verify deploy and rollback avoid destructive git commands and track releases."""
    deploy_path = os.path.join(INFRA_DIR, "deploy.sh")
    rollback_path = os.path.join(INFRA_DIR, "rollback.sh")

    deploy_content = open(deploy_path, "r", encoding="utf-8").read()
    rollback_content = open(rollback_path, "r", encoding="utf-8").read()

    # Destructive resets must never be used
    assert "git reset --hard" not in deploy_content
    assert "git reset --hard" not in rollback_content

    # Release tracking files
    assert ".current_release" in deploy_content
    assert ".previous_release" in deploy_content
    assert ".previous_release" in rollback_content
