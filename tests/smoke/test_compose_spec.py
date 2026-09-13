"""
Smoke tests for Phase 6 Docker Compose runtime specification.
Verifies service topology, dependencies, volume persistence, health checks,
and static validation via `docker compose config`.
"""

import subprocess
import yaml
from pathlib import Path

COMPOSE_FILE = Path(__file__).resolve().parent.parent.parent / "infra" / "docker-compose.yml"


def test_compose_yaml_valid_and_services_present():
    """Verifies that docker-compose.yml is valid YAML and includes all 3 services for systemd-native deploy."""
    assert COMPOSE_FILE.exists(), f"Missing compose file at {COMPOSE_FILE}"
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    services = spec.get("services", {})
    # Under systemd-native deploy model, ONLY db, redis, and caddy stay in Docker.
    # api, worker, and outbox-dispatcher run natively via systemd.
    required_services = {"db", "redis", "caddy"}
    assert required_services.issubset(set(services.keys())), (
        f"Missing required services: {required_services - set(services.keys())}"
    )


def test_db_and_redis_healthchecks_and_volumes():
    """Verifies db and redis health checks, persistent volumes, and published ports."""
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    services = spec["services"]
    volumes = spec.get("volumes", {})

    # DB verification
    db = services["db"]
    assert "postgres:16" in db["image"]
    assert "healthcheck" in db
    assert "postgres_data" in volumes
    # Native processes reach DB via localhost:5432
    assert any("5432:5432" in str(p) for p in db.get("ports", []))

    # Redis verification
    redis = services["redis"]
    assert "redis:7" in redis["image"]
    assert "healthcheck" in redis
    assert "redis_data" in volumes
    # Native processes reach Redis via localhost:6379
    assert any("6379:6379" in str(p) for p in redis.get("ports", []))


def test_caddy_reverse_proxy_configuration():
    """Verifies Caddy uses host networking to route to native uvicorn process on loopback."""
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    caddy = spec["services"]["caddy"]
    assert caddy.get("network_mode") == "host"
    assert "caddy_data" in spec.get("volumes", {})
    assert "caddy_config" in spec.get("volumes", {})


def test_docker_compose_config_validation():
    """Verifies `docker compose config` command returns 0 with no syntax or schema errors."""
    res = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
        capture_output=True,
        text=True,
    )
    err_msg = res.stderr or ""
    assert res.returncode == 0, f"docker compose config failed: {err_msg}"
