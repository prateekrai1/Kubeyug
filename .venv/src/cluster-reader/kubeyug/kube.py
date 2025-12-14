from kubernetes import client, config
import json

NAMESPACE = "kubeyug"


def load_cluster_capabilities():
    """
    Preferred source: ConfigMaps written by agent.py (label app=kubeyug-node-capabilities).
    Fallback: if none exist, query nodes directly.
    """
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

    # Fallback path: no agent ConfigMaps yet
    if not caps:
        nodes = v1.list_node().items
        for node in nodes:
            info = node.status.node_info
            meta = node.metadata
            caps.append(
                {
                    "nodeName": meta.name,
                    "arch": meta.labels.get("kubernetes.io/arch"),
                    "os": meta.labels.get("kubernetes.io/os"),
                    "kernel": info.kernel_version,
                    "kubeletVersion": info.kubelet_version,
                    "capacity": {
                        "cpu": node.status.capacity.get("cpu"),
                        "memory": node.status.capacity.get("memory"),
                    },
                }
            )

    return caps


def detect_cluster_profile(caps: list[dict]) -> str:
    """
    Returns: minikube | kind | eks | generic
    Uses only fields already present in caps (nodeName, etc.).
    """
    names = [str(c.get("nodeName", "")).lower() for c in caps]

    if any(n == "minikube" or n.startswith("minikube") for n in names):
        return "minikube"
    if any("kind-control-plane" in n or n.startswith("kind-") for n in names):
        return "kind"
    if any(n.startswith("ip-") for n in names):  # common on EKS/EC2
        return "eks"

    return "generic"


def summarize_cluster(caps):
    nodes = len(caps)
    arches = sorted({c.get("arch") for c in caps if c.get("arch")})
    oses = sorted({c.get("os") for c in caps if c.get("os")})

    total_cpu = 0
    for c in caps:
        cpu = (c.get("capacity") or {}).get("cpu")
        try:
            total_cpu += int(cpu)
        except Exception:
            pass

    return {"nodes": nodes, "arches": arches, "oses": oses, "totalCpu": total_cpu}
