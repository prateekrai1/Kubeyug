from __future__ import annotations

import json
from datetime import datetime, timezone
from kubernetes import client, config
from kubernetes.client.rest import ApiException

STATE_NAMESPACE = "kubeyug"
STATE_CONFIGMAP_NAME = "kubeyug-state"
STATE_KEY = "kubeyug-state.json"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _core_v1() -> client.CoreV1Api:
    # Uses kubeconfig on your dev machine.
    config.load_kube_config()
    return client.CoreV1Api()


def read_state() -> dict:
    """
    Returns:
    {
      "version": 1,
      "updatedAt": "...",
      "installs": [
        {"toolKey": "...", "namespace": "...", "chart": "...", "release": "...", "lastAction": "...", "timestamp": "..."}
      ]
    }
    """
    v1 = _core_v1()
    try:
        cm = v1.read_namespaced_config_map(STATE_CONFIGMAP_NAME, STATE_NAMESPACE)
        raw = (cm.data or {}).get(STATE_KEY, "")
        if not raw:
            return {"version": 1, "updatedAt": _now_iso(), "installs": []}
        return json.loads(raw)
    except ApiException as e:
        if e.status == 404:
            return {"version": 1, "updatedAt": _now_iso(), "installs": []}
        raise


def write_state(state: dict) -> None:
    v1 = _core_v1()

    state = dict(state)
    state["updatedAt"] = _now_iso()

    body = client.V1ConfigMap(
        metadata=client.V1ObjectMeta(
            name=STATE_CONFIGMAP_NAME,
            namespace=STATE_NAMESPACE,
        ),
        data={STATE_KEY: json.dumps(state, indent=2)},
    )

    try:
        v1.create_namespaced_config_map(namespace=STATE_NAMESPACE, body=body)
    except ApiException as e:
        # 409 = already exists; replace it.
        if e.status != 409:
            raise
        v1.replace_namespaced_config_map(
            name=STATE_CONFIGMAP_NAME,
            namespace=STATE_NAMESPACE,
            body=body,
        )


def record_install(*, tool_key: str, namespace: str, chart: str, release: str) -> dict:
    state = read_state()
    installs = state.setdefault("installs", [])
    installs.append(
        {
            "toolKey": tool_key,
            "namespace": namespace,
            "chart": chart,
            "release": release,
            "lastAction": "install_or_upgrade",
            "timestamp": _now_iso(),
        }
    )
    write_state(state)
    return state


def record_uninstall(*, tool_key: str, namespace: str, release: str) -> dict:
    state = read_state()
    installs = state.setdefault("installs", [])
    installs.append(
        {
            "toolKey": tool_key,
            "namespace": namespace,
            "chart": None,
            "release": release,
            "lastAction": "uninstall",
            "timestamp": _now_iso(),
        }
    )
    write_state(state)
    return state
