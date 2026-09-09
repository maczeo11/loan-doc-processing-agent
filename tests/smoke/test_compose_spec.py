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
    """Verifies that docker-compose.yml is valid YAML and includes all 7 required services."""
    assert COMPOSE_FILE.exists(), f"Missing compose file at {COMPOSE_FILE}"
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    services = spec.get("services", {})
    required_services = {"db", "redis", "migrate", "api", "outbox-dispatcher", "worker", "caddy"}
    assert required_services.issubset(set(services.keys())), (
        f"Missing required services: {required_services - set(services.keys())}"
    )


def test_db_and_redis_healthchecks_and_volumes():
    """Verifies db and redis health checks and persistent volume declarations."""
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    services = spec["services"]
    volumes = spec.get("volumes", {})

    # DB verification
    db = services["db"]
    assert "postgres:16" in db["image"]
    assert "healthcheck" in db
    assert "postgres_data" in volumes

    # Redis verification
    redis = services["redis"]
    assert "redis:7" in redis["image"]
    assert "healthcheck" in redis
    assert "redis_data" in volumes


def test_migration_and_startup_dependency_order():
    """Verifies one-shot migration and downstream dependency conditions."""
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    services = spec["services"]

    # Migrate service runs alembic upgrade head
    migrate = services["migrate"]
    assert migrate["command"] == ["alembic", "upgrade", "head"]
    assert migrate["depends_on"]["db"]["condition"] == "service_healthy"

    # API, Dispatcher, Worker must wait for migrate to complete successfully
    for s_name in ("api", "outbox-dispatcher", "worker"):
        s = services[s_name]
        assert "migrate" in s["depends_on"]
        assert s["depends_on"]["migrate"]["condition"] == "service_completed_successfully"
        assert s["depends_on"]["db"]["condition"] == "service_healthy"


def test_shared_storage_volume_mounted():
    """Verifies shared dossiers_storage volume is mounted in both api and worker."""
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    services = spec["services"]
    volumes = spec.get("volumes", {})
    assert "dossiers_storage" in volumes

    api_vols = [str(v) for v in services["api"]["volumes"]]
    worker_vols = [str(v) for v in services["worker"]["volumes"]]

    assert any("dossiers_storage" in v for v in api_vols)
    assert any("dossiers_storage" in v for v in worker_vols)


def test_caddy_reverse_proxy_configuration():
    """Verifies Caddy reverse proxy maps port 80 and depends on API."""
    with open(COMPOSE_FILE, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    caddy = spec["services"]["caddy"]
    assert any("80:80" in str(p) for p in caddy["ports"])
    assert "api" in caddy["depends_on"]


def test_docker_compose_config_validation():
    """Verifies `docker compose config` command returns 0 with no syntax or schema errors."""
    res = subprocess.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "config"],
        capture_output=True,
        text=True,
    )
    err_msg = res.stderr or ""
    assert res.returncode == 0, f"docker compose config failed: {err_msg}"
