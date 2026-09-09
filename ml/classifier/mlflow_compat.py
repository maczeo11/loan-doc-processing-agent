"""
MLflow Compatibility Adapter for FinScan AI Classifier.
Owned by Member 5 (Karthik).

Delegates to official `mlflow` package if installed.
If `mlflow` is not installed (e.g. offline isolated environment), provides a robust
local file-based shim conforming to MLflow's local directory layout:
./mlruns/<experiment_id>/<run_id>/{params,metrics,artifacts,tags}
"""

import os
import sys
import time
import shutil
import uuid
from typing import Dict, Any, Optional, Union

try:
    import mlflow as _real_mlflow
    _HAS_REAL_MLFLOW = True
except ImportError:
    _real_mlflow = None
    _HAS_REAL_MLFLOW = False


class _LocalRunContext:
    def __init__(self, run_id: str, run_name: Optional[str], experiment_id: str = "0", tracking_dir: str = "./mlruns"):
        self.run_id = run_id
        self.run_name = run_name or f"run_{run_id[:8]}"
        self.experiment_id = experiment_id
        self.tracking_dir = os.path.abspath(tracking_dir)
        self.run_dir = os.path.join(self.tracking_dir, self.experiment_id, self.run_id)
        self.start_time = int(time.time() * 1000)

        # Initialize directory layout
        for d in ["params", "metrics", "artifacts", "tags"]:
            os.makedirs(os.path.join(self.run_dir, d), exist_ok=True)

        # Write experiment meta.yaml if missing
        exp_dir = os.path.join(self.tracking_dir, self.experiment_id)
        exp_meta = os.path.join(exp_dir, "meta.yaml")
        if not os.path.exists(exp_meta):
            with open(exp_meta, "w", encoding="utf-8") as f:
                f.write(
                    f"artifact_location: {exp_dir}\n"
                    f"creation_time: {self.start_time}\n"
                    f"experiment_id: '{self.experiment_id}'\n"
                    f"last_update_time: {self.start_time}\n"
                    f"lifecycle_stage: active\n"
                    f"name: default\n"
                )

        # Write run meta.yaml
        with open(os.path.join(self.run_dir, "meta.yaml"), "w", encoding="utf-8") as f:
            f.write(
                f"artifact_uri: {os.path.join(self.run_dir, 'artifacts')}\n"
                f"end_time: null\n"
                f"experiment_id: '{self.experiment_id}'\n"
                f"lifecycle_stage: active\n"
                f"run_id: {self.run_id}\n"
                f"run_name: {self.run_name}\n"
                f"start_time: {self.start_time}\n"
                f"status: RUNNING\n"
                f"user_id: karthik\n"
            )

        # Write tag for run name
        with open(os.path.join(self.run_dir, "tags", "mlflow.runName"), "w", encoding="utf-8") as f:
            f.write(self.run_name)

    def log_param(self, key: str, value: Any):
        param_file = os.path.join(self.run_dir, "params", str(key))
        with open(param_file, "w", encoding="utf-8") as f:
            f.write(str(value))

    def log_params(self, params: Dict[str, Any]):
        for k, v in params.items():
            self.log_param(k, v)

    def log_metric(self, key: str, value: float, step: Optional[int] = 0):
        metric_file = os.path.join(self.run_dir, "metrics", str(key))
        ts = int(time.time() * 1000)
        st = step if step is not None else 0
        with open(metric_file, "a", encoding="utf-8") as f:
            f.write(f"{ts} {float(value)} {st}\n")

    def log_metrics(self, metrics: Dict[str, float], step: Optional[int] = 0):
        for k, v in metrics.items():
            self.log_metric(k, v, step=step)

    def log_artifact(self, local_path: str, artifact_path: Optional[str] = None):
        if not os.path.exists(local_path):
            return
        dest_dir = os.path.join(self.run_dir, "artifacts")
        if artifact_path:
            dest_dir = os.path.join(dest_dir, artifact_path)
        os.makedirs(dest_dir, exist_ok=True)
        if os.path.isfile(local_path):
            shutil.copy2(local_path, dest_dir)
        elif os.path.isdir(local_path):
            shutil.copytree(local_path, os.path.join(dest_dir, os.path.basename(local_path)), dirs_exist_ok=True)

    def set_tag(self, key: str, value: Any):
        tag_file = os.path.join(self.run_dir, "tags", str(key))
        with open(tag_file, "w", encoding="utf-8") as f:
            f.write(str(value))

    def end(self, status: str = "FINISHED"):
        end_time = int(time.time() * 1000)
        meta_file = os.path.join(self.run_dir, "meta.yaml")
        if os.path.exists(meta_file):
            with open(meta_file, "r", encoding="utf-8") as f:
                content = f.read()
            content = content.replace("end_time: null", f"end_time: {end_time}")
            content = content.replace("status: RUNNING", f"status: {status}")
            with open(meta_file, "w", encoding="utf-8") as f:
                f.write(content)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        status = "FAILED" if exc_type else "FINISHED"
        self.end(status=status)
        global _CURRENT_RUN
        _CURRENT_RUN = None
        return False


_TRACKING_URI = "./mlruns"
_CURRENT_EXPERIMENT = "0"
_CURRENT_RUN: Optional[Union[_LocalRunContext, Any]] = None


def set_tracking_uri(uri: str):
    global _TRACKING_URI
    _TRACKING_URI = uri
    if _HAS_REAL_MLFLOW:
        _real_mlflow.set_tracking_uri(uri)


def set_experiment(experiment_name: str):
    global _CURRENT_EXPERIMENT
    _CURRENT_EXPERIMENT = experiment_name
    if _HAS_REAL_MLFLOW:
        _real_mlflow.set_experiment(experiment_name)


def start_run(run_name: Optional[str] = None, **kwargs):
    global _CURRENT_RUN
    if _HAS_REAL_MLFLOW:
        _CURRENT_RUN = _real_mlflow.start_run(run_name=run_name, **kwargs)
        return _CURRENT_RUN

    run_id = uuid.uuid4().hex
    _CURRENT_RUN = _LocalRunContext(
        run_id=run_id,
        run_name=run_name,
        experiment_id=_CURRENT_EXPERIMENT,
        tracking_dir=_TRACKING_URI
    )
    return _CURRENT_RUN


def log_param(key: str, value: Any):
    if _HAS_REAL_MLFLOW:
        _real_mlflow.log_param(key, value)
    elif _CURRENT_RUN:
        _CURRENT_RUN.log_param(key, value)


def log_params(params: Dict[str, Any]):
    if _HAS_REAL_MLFLOW:
        _real_mlflow.log_params(params)
    elif _CURRENT_RUN:
        _CURRENT_RUN.log_params(params)


def log_metric(key: str, value: float, step: Optional[int] = None):
    if _HAS_REAL_MLFLOW:
        _real_mlflow.log_metric(key, value, step=step)
    elif _CURRENT_RUN:
        _CURRENT_RUN.log_metric(key, value, step=step)


def log_metrics(metrics: Dict[str, float], step: Optional[int] = None):
    if _HAS_REAL_MLFLOW:
        _real_mlflow.log_metrics(metrics, step=step)
    elif _CURRENT_RUN:
        _CURRENT_RUN.log_metrics(metrics, step=step)


def log_artifact(local_path: str, artifact_path: Optional[str] = None):
    if _HAS_REAL_MLFLOW:
        _real_mlflow.log_artifact(local_path, artifact_path=artifact_path)
    elif _CURRENT_RUN:
        _CURRENT_RUN.log_artifact(local_path, artifact_path=artifact_path)


def set_tag(key: str, value: Any):
    if _HAS_REAL_MLFLOW:
        _real_mlflow.set_tag(key, value)
    elif _CURRENT_RUN:
        _CURRENT_RUN.set_tag(key, value)


def end_run(status: str = "FINISHED"):
    global _CURRENT_RUN
    if _HAS_REAL_MLFLOW:
        _real_mlflow.end_run(status=status)
    elif _CURRENT_RUN:
        _CURRENT_RUN.end(status=status)
    _CURRENT_RUN = None
