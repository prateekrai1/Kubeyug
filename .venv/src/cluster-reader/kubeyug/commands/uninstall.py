from kubeyug.registry import find_tool
from kubeyug.helm_ops import run_cmd


def cmd_uninstall(args):
    found = find_tool(args.key)
    if not found:
        raise SystemExit(f"Unknown tool key: {args.key}")

    _, tool = found
    ns = args.namespace or tool["namespace"]
    release = args.release or args.key

    print(f"Uninstalling {tool['name']} (release={release}) from namespace '{ns}' via Helm...\n")

    cmd = ["helm", "uninstall", release, "-n", ns]

    # Optional flags (Helm supports these) [web:630]
    if args.wait:
        cmd.append("--wait")
    if args.timeout:
        cmd += ["--timeout", args.timeout]
    if args.no_hooks:
        cmd.append("--no-hooks")

    run_cmd(cmd, dry_run=args.dry_run)


def register_uninstall_command(subparsers):
    p = subparsers.add_parser("uninstall", help="Uninstall a tool (Helm release) by tool key")
    p.add_argument("key", help="Tool key, e.g. prometheus, cilium, argo")
    p.add_argument("--namespace", help="Override namespace from registry")
    p.add_argument("--release", help="Override Helm release name (default: same as key)")
    p.add_argument("--wait", action="store_true", help="Wait for resources to be deleted")
    p.add_argument("--timeout", help="Helm timeout (e.g. 5m, 2m30s)")
    p.add_argument("--no-hooks", action="store_true", help="Do not run Helm hooks")
    p.add_argument("--dry-run", action="store_true", help="Print command without executing")
    p.set_defaults(func=cmd_uninstall)
