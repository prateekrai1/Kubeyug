from kubernetes import client, config
import json
import sys
import subprocess

NAMESPACE = "kubeyug"

TOOL_REGISTRY = {
    "monitoring": [
        {
            "key": "prometheus",
            "name": "Prometheus",
            "helm_repo_name": "prometheus-community",
            "helm_repo_url": "https://prometheus-community.github.io/helm-charts",
            "helm_chart": "prometheus-community/prometheus",
            "namespace": "monitoring",
        },
        {
            "key": "opentelemetry",
            "name": "OpenTelemetry Collector",
            "helm_repo_name": "open-telemetry",
            "helm_repo_url": "https://open-telemetry.github.io/opentelemetry-helm-charts",
            "helm_chart": "open-telemetry/opentelemetry-collector",
            "namespace": "observability",
        },
    ]
}



def load_cluster_capabilities():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    cms = v1.list_namespaced_config_map(
        namespace=NAMESPACE,
        label_selector="app=kubeyug-node-capabilities",
    ).items

    caps = []
    for cm in cms:
        data = cm.data.get("capabilities.json")
        if not data:
            continue
        caps.append(json.loads(data))
    return caps

def find_tool_by_key(category: str, key: str) -> dict | None:
    for t in TOOL_REGISTRY.get(category, []):
        if t["key"] == key:
            return t
    return None

def install_monitoring():
    caps = load_cluster_capabilities()
    summary = summarize_cluster(caps)
    tools = TOOL_REGISTRY["monitoring"]
    decision = decide_monitoring_stack(summary, tools)

    tool_key = decision["chartKey"]
    tool = find_tool_by_key("monitoring", tool_key)
    if not tool:
        print(f"No tool found for key '{tool_key}'")
        return

    ns = tool["namespace"]
    repo_name = tool["helm_repo_name"]
    repo_url = tool["helm_repo_url"]
    chart = tool["helm_chart"]

    print("Cluster summary:", summary)
    print("Decision:", decision)
    print(f"\nInstalling {tool['name']} into namespace '{ns}' via Helm...\n")

    cmds = [
        ["helm", "repo", "add", repo_name, repo_url],
        ["helm", "repo", "update"],
        ["helm", "install", tool_key, chart, "-n", ns, "--create-namespace"],
    ]

    for cmd in cmds:
        print(">", " ".join(cmd))
        subprocess.run(cmd, check=True)


def summarize_cluster(caps):
    nodes = len(caps)
    arches = sorted({c["arch"] for c in caps})
    oses = sorted({c["os"] for c in caps})
    total_cpu = sum(int(c["capacity"]["cpu"]) for c in caps)
    return {
        "nodes": nodes,
        "arches": arches,
        "oses": oses,
        "totalCpu": total_cpu
    }

def decide_monitoring_stack(cluster_summary: dict, tools: list[dict]) -> dict:
    return {
        "tool": "prometheus",
        "reason": "Single-node or small cluster; Prometheus alone is enough for basic monitoring.",
        "chartKey": "prometheus"
    }

def run_decision():
    caps = load_cluster_capabilities()
    summary = summarize_cluster(caps)
    tools = TOOL_REGISTRY["monitoring"]
    decision = decide_monitoring_stack(summary, tools)

    print("Decision:")
    print(json.dumps({
        "cluster": summary,
        "decision": decision
    }, indent=2))

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        cmd = sys.argv[1]

        if cmd == "monitoring":
            run_decision()
        elif cmd == "install-monitoring":
            install_monitoring()
        else:
            print(f"Unknown command: {cmd}")
    else:
        print(json.dumps(load_cluster_capabilities(), indent=2))

    caps = load_cluster_capabilities()
    print(json.dumps(caps, indent=2))