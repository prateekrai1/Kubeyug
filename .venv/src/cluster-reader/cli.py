from kubernetes import client, config
import argparse
import json
import os
import subprocess

NAMESPACE = "kubeyug"

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(HERE, "data")
TOOL_REGISTRY_PATH = os.path.join(DATA_DIR, "tool_registry.json")


def load_tool_registry() -> dict:
    with open(TOOL_REGISTRY_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


TOOL_REGISTRY = load_tool_registry()


def load_cluster_capabilities():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    cms = v1.list_namespaced_config_map(
        namespace=NAMESPACE,
        label_selector="app=kubeyug-node-capabilities",
    ).items

    caps = []
    for cm in cms:
        data = (cm.data or {}).get("capabilities.json")
        if not data:
            continue
        caps.append(json.loads(data))
    return caps


def summarize_cluster(caps):
    nodes = len(caps)
    arches = sorted({c["arch"] for c in caps})
    oses = sorted({c["os"] for c in caps})
    total_cpu = sum(int(c["capacity"]["cpu"]) for c in caps)
    return {"nodes": nodes, "arches": arches, "oses": oses, "totalCpu": total_cpu}


def find_tool(key: str) -> tuple[str, dict] | None:
    """Search all categories and return (category, tool)."""
    for category, tools in TOOL_REGISTRY.items():
        for t in tools:
            if t.get("key") == key:
                return category, t
    return None


def decide_monitoring_stack(cluster_summary: dict, tools: list[dict]) -> dict:
    # Need to replace with Oumi call. 
    return {
        "tool": "prometheus",
        "reason": "Single-node or small cluster; Prometheus alone is enough for basic monitoring.",
        "chartKey": "prometheus",
    }


def run_cmd(cmd: list[str], dry_run: bool = False, capture: bool = False):
    print(">", " ".join(cmd))
    if dry_run:
        return None
    return subprocess.run(
        cmd,
        check=True,
        text=True,
        capture_output=capture,
    )


def helm_apply_release(
    release: str,
    chart: str,
    namespace: str,
    repo_name: str,
    repo_url: str,
    dry_run: bool = False,
):
    run_cmd(["helm", "repo", "add", repo_name, repo_url], dry_run=dry_run)
    run_cmd(["helm", "repo", "update"], dry_run=dry_run)
    run_cmd(
        [
            "helm",
            "upgrade",
            "--install",
            release,
            chart,
            "-n",
            namespace,
            "--create-namespace",
        ],
        dry_run=dry_run,
    )


def install_key_as_helm(key: str, namespace_override: str | None = None, dry_run: bool = False):
    found = find_tool(key)
    if not found:
        raise SystemExit(f"Unknown tool key: {key}")

    _, tool = found
    ns = namespace_override or tool["namespace"]

    print(f"Installing/updating {tool['name']} (key={key}) in namespace '{ns}' via Helm...\n")

    helm_apply_release(
        release=key,
        chart=tool["helm_chart"],
        namespace=ns,
        repo_name=tool["helm_repo_name"],
        repo_url=tool["helm_repo_url"],
        dry_run=dry_run,
    )


def install_monitoring_smart(namespace_override: str | None = None, dry_run: bool = False):
    caps = load_cluster_capabilities()
    summary = summarize_cluster(caps)

    tools = TOOL_REGISTRY.get("monitoring", [])
    if not tools:
        raise SystemExit("No 'monitoring' category found in tool_registry.json")

    decision = decide_monitoring_stack(summary, tools)
    tool_key = decision["chartKey"]

    print("Cluster summary:", summary)
    print("Decision:", decision, "\n")

    install_key_as_helm(tool_key, namespace_override=namespace_override, dry_run=dry_run)


def main():
    parser = argparse.ArgumentParser(prog="kubeyug")
    sub = parser.add_subparsers(dest="command")

    p_mon = sub.add_parser("monitoring", help="Suggest monitoring stack")
    p_mon.add_argument("--json", action="store_true", help="Print machine-readable JSON")

    p_install = sub.add_parser("install", help="Install a tool or stack")
    p_install.add_argument("target", help="e.g. 'monitoring' or a tool key like 'prometheus'")
    p_install.add_argument("--helm", action="store_true", help="Force Helm install for the target key")
    p_install.add_argument("--namespace", help="Override target namespace")
    p_install.add_argument("--dry-run", action="store_true", help="Print commands without executing")

    args = parser.parse_args()

    if args.command == "monitoring":
        caps = load_cluster_capabilities()
        summary = summarize_cluster(caps)
        tools = TOOL_REGISTRY.get("monitoring", [])
        decision = decide_monitoring_stack(summary, tools)
        out = {"cluster": summary, "decision": decision}
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print("Decision:")
            print(json.dumps(out, indent=2))
        return

    if args.command == "install":
        if args.target == "monitoring" and not args.helm:
            install_monitoring_smart(namespace_override=args.namespace, dry_run=args.dry_run)
            return

        install_key_as_helm(args.target, namespace_override=args.namespace, dry_run=args.dry_run)
        return

    caps = load_cluster_capabilities()
    print(json.dumps(caps, indent=2))


if __name__ == "__main__":
    main()
