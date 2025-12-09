from kubernetes import client, config
import json

NAMESPACE = "kubeyug"

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

if __name__ == "__main__":
    caps = load_cluster_capabilities()
    print(json.dumps(caps, indent=2))