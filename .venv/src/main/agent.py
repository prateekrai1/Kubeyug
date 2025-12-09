from kubernetes import client, config
from kubernetes.client.rest import ApiException
import json
import os

NAMESPACE = "kubeyug"

def get_node_name():
    # For now, just read from env; later this will be set via Downward API in the Pod
    return os.environ.get("KUBEYUG_NODE_NAME")

def get_cluster_capabilities():
    # Use local kubeconfig for now
    config.load_kube_config()  # later: config.load_incluster_config() [web:216][web:228]

    v1 = client.CoreV1Api()
    nodes = v1.list_node().items

    caps = []
    for node in nodes:
        info = node.status.node_info
        meta = node.metadata

        caps.append({
            "nodeName": meta.name,
            "arch": node.metadata.labels.get("kubernetes.io/arch"),
            "os": node.metadata.labels.get("kubernetes.io/os"),
            "kernel": info.kernel_version,
            "kubeletVersion": info.kubelet_version,
            "capacity": {
                "cpu": node.status.capacity.get("cpu"),
                "memory": node.status.capacity.get("memory"),
            },
        })

    return caps

def ensure_namespace():
    config.load_kube_config()
    v1 = client.CoreV1Api()

    ns_body = client.V1Namespace(
        metadata=client.V1ObjectMeta(name=NAMESPACE)
    )

    try:
        v1.create_namespace(ns_body)
        print(f"Created namespace {NAMESPACE}")
    except ApiException as e:
        if e.status == 409:
            print(f"Namespace {NAMESPACE} already exists")
        else:
            raise

def upsert_configmap_for_node(node_name:str, caps:dict):
    config.load_kube_config()
    v1 = client.CoreV1Api()
    cm_name = f"kubeyug-node-{node_name}"
    data_json = json.dumps(caps, indent=2)
    body = client.V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=client.V1ObjectMeta(
            name=cm_name,
            namespace=NAMESPACE,
            labels={"app": "kubeyug-node-capabilities"},
        ),
        data={"capabilities.json": data_json},
    ) 
    try:
        v1.create_namespaced_config_map(namespace=NAMESPACE, body=body)
        print(f"Created ConfigMap {cm_name} in {NAMESPACE}")
    except ApiException as e:
        if e.status == 409:
            v1.replace_namespaced_config_map(name=cm_name, namespace=NAMESPACE, body=body)
            print(f"Updated ConfigMap {cm_name} in {NAMESPACE}")
        else:
            raise


if __name__ == "__main__":
    ensure_namespace()
    caps = get_cluster_capabilities()
    for node_name, caps in caps.items():
        upsert_configmap_for_node(node_name, caps)
    print(json.dumps(caps, indent=2))
