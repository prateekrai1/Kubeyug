from kubeyug.registry import find_tool, load_tool_registry
from kubeyug.kube import load_cluster_capabilities, summarize_cluster
from kubeyug.helm_ops import helm_apply_release


def decide_monitoring_stack(cluster_summary: dict, tools: list[dict], use_oumi: bool) -> dict:
    """
    Demo behavior:
    - Default: deterministic safe choice (prometheus).
    - Optional: if --oumi is passed, then try Oumi (lazy import so startup stays fast).
    """
    if not use_oumi:
        return {
            "tool": "prometheus",
            "reason": "Demo default: Prometheus is enough for basic monitoring.",
            "chartKey": "prometheus",
        }

    try:
        from kubeyug.oumi.oumi_client import OumiClient
    except Exception as e:
        return {
            "tool": "prometheus",
            "reason": f"Oumi not available ({type(e).__name__}); falling back to Prometheus.",
            "chartKey": "prometheus",
        }

    client = OumiClient()
    return client.decide(goal="monitoring", cluster_summary=cluster_summary, tools=tools)


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


def install_monitoring_smart(namespace_override: str | None, dry_run: bool, use_oumi: bool):
    caps = load_cluster_capabilities()
    summary = summarize_cluster(caps)

    reg = load_tool_registry()
    tools = reg.get("monitoring", [])
    if not tools:
        raise SystemExit("No monitoring tools found in registry.")

    decision = decide_monitoring_stack(summary, tools=tools, use_oumi=use_oumi)
    tool_key = decision.get("chartKey")
    if not tool_key:
        raise SystemExit("Decision did not return chartKey.")

    print("Cluster summary:", summary)
    print("Decision:", decision, "\n")

    install_key_as_helm(tool_key, namespace_override=namespace_override, dry_run=dry_run)


def cmd_install(args):
    if args.target == "monitoring" and not args.helm:
        install_monitoring_smart(
            namespace_override=args.namespace,
            dry_run=args.dry_run,
            use_oumi=args.oumi,
        )
        return

    install_key_as_helm(args.target, namespace_override=args.namespace, dry_run=args.dry_run)


def register_install_command(subparsers):
    p = subparsers.add_parser("install", help="Install a tool or stack")
    p.add_argument("target", help="e.g. 'monitoring' or a tool key like 'prometheus'")
    p.add_argument("--helm", action="store_true", help="Force Helm install for the target key")
    p.add_argument("--namespace", help="Override namespace from registry")
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing")

    # New: opt-in flag to use Oumi (kept off by default to keep startup fast)
    p.add_argument("--oumi", action="store_true", help="Use Oumi to decide (slow; optional)")

    p.set_defaults(func=cmd_install)
