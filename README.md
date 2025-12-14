# Kubeyug

Kubeyug is a CLI that installs and manages common Kubernetes add-ons using a curated tool registry (Helm repos/charts + default namespaces).

## What is Kubeyug?

Kubeyug provides a single interface to install, uninstall, inspect, and roll back popular Kubernetes tooling (monitoring, networking, GitOps, logging, etc.) using Helm.
It also supports collecting cluster/node capabilities into ConfigMaps so higher-level logic (like “smart installs”) can make decisions based on the cluster environment.

## What problem does it solve?

Installing add-ons repeatedly across clusters usually means remembering Helm repos, chart names, namespaces, and doing the same steps every time. 
Kubeyug centralizes this in a registry and exposes consistent lifecycle commands (install/status/history/rollback/uninstall) so you don’t have to re-learn each tool’s install steps.

---

## Installation (from Git)

```python -m pip install "kubeyug @ git+https://github.com/prateekrai1/Kubeyug.git" ```

### Verify:
```kubeyug --version```
```kubeyug --help```

The agent writes one ConfigMap per node into the `kubeyug` namespace with label `app=kubeyug-node-capabilities` and a `capabilities.json` key.

---

## Tools supported so far

These tool keys are currently shipped in the registry (grouped by category).

### Networking
- `cilium` (Cilium) 
- `istio` (Istio) 
- `envoy` (Envoy) 

### Monitoring / observability
- `prometheus` (Prometheus) 
- `jaeger` (Jaeger)
- `opencost` (OpenCost)

### GitOps
- `argo` (Argo CD) 

### Databases
- `vitess` (Vitess) 

### Security
- `kyverno` (Kyverno)

### Logging
- `fluentd` (Fluentd)

---
## Oumi usage (LLM integration)

Kubeyug includes an Oumi-based decision layer intended to choose the best tool for a goal given the cluster summary and the available tools in the registry.  
The integration is implemented as `OumiClient`, which calls an OpenAI-compatible endpoint via Oumi’s `OpenAIInferenceEngine` and expects a strict JSON response containing `chartKey`, `reason`, and optional `confidence`.

### How it’s used today
- The “smart monitoring install” flow is present (`kubeyug install monitoring`), but the current decision function is still hardcoded and marked “TODO: replace with Oumi later”.

### How to enable it (planned wiring)
Once the `install monitoring` decision is switched to use `OumiClient().decide(...)`, the model endpoint can be configured using environment variables (all read by Kubeyug at runtime).
- `KUBEYUG_LLM_MODEL` (default: `gpt-4o-mini`)
- `KUBEYUG_LLM_BASE_URL` (OpenAI-compatible endpoint, e.g. vLLM server URL) 
- `KUBEYUG_LLM_API_KEY` 
- `KUBEYUG_LLM_MAX_NEW_TOKENS` (default: 256) 
- `KUBEYUG_LLM_TEMPERATURE` (default: 0.1) 


## Notes
- Kubeyug expects `helm` and `kubectl` to be available and your kubeconfig to point at the target cluster (since installs and the agent both interact with Kubernetes).



