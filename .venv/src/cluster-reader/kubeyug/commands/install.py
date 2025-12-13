from kubeyug.registry import find_tool, load_tool_registry
from kubeyug.kube import load_cluster_capabilities, summarize_cluster
from kubeyug.helm_ops import helm_apply_release


def decide_monitoring_stack(cluster_summary: dict, tools: list[dict]) -> dict:
    # TODO: replace with Oumi later
    return {
        "tool": "prometheus",
        "reason": "Single-node or small cluster; Prometheus alone is enough for basic monitoring.",
        "chartKey": "prometheus",
    }


def install_key_as_helm(key: str, namespace_override: str | None, dry_run: bool):
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

    if not dry_run:
        from kubeyug.state import record_install
        record_install(tool_key=key, namespace=ns, chart=tool["helm_chart"], release=key)


def install_monitoring_smart(namespace_override: str | None, dry_run: bool):
    caps = load_cluster_capabilities()
    summary = summarize_cluster(caps)

    reg = load_tool_registry()
    tools = reg.get("monitoring", [])

    decision = decide_monitoring_stack(summary, tools=tools)
    tool_key = decision["chartKey"]

    print("Cluster summary:", summary)
    print("Decision:", decision, "\n")

    install_key_as_helm(tool_key, namespace_override=namespace_override, dry_run=dry_run)


def cmd_install(args):
    if args.target == "monitoring" and not args.helm:
        install_monitoring_smart(namespace_override=args.namespace, dry_run=args.dry_run)
        return
    install_key_as_helm(args.target, namespace_override=args.namespace, dry_run=args.dry_run)


def register_install_command(subparsers):
    p = subparsers.add_parser("install", help="Install a tool or stack")
    p.add_argument("target", help="e.g. 'monitoring' or a tool key like 'prometheus'")
    p.add_argument("--helm", action="store_true", help="Force Helm install for the target key")
    p.add_argument("--namespace", help="Override namespace from registry")
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    p.set_defaults(func=cmd_install)
