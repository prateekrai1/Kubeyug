import json
from kubeyug.registry import find_tool
from kubeyug.helm_ops import run_cmd


def _helm_history(release: str, namespace: str, dry_run: bool) -> list[dict]:
    # helm history supports -o json, which makes parsing easy. [web:665]
    res = run_cmd(
        ["helm", "history", release, "-n", namespace, "-o", "json"],
        dry_run=dry_run,
        capture=True,
    )
    if res is None:
        return []
    return json.loads(res.stdout or "[]")


def cmd_history(args):
    found = find_tool(args.key)
    if not found:
        raise SystemExit(f"Unknown tool key: {args.key}")

    _, tool = found
    ns = args.namespace or tool["namespace"]
    release = args.release or args.key

    hist = _helm_history(release, ns, dry_run=args.dry_run)
    if args.json:
        print(json.dumps(hist, indent=2))
        return

    if not hist:
        print("No history (or dry-run).")
        return

    # Keep output short and useful
    for row in hist[-min(len(hist), args.max):]:
        rev = row.get("revision")
        status = row.get("status")
        updated = row.get("updated")
        chart = row.get("chart")
        print(f"rev={rev} status={status} updated={updated} chart={chart}")


def cmd_rollback(args):
    found = find_tool(args.key)
    if not found:
        raise SystemExit(f"Unknown tool key: {args.key}")

    _, tool = found
    ns = args.namespace or tool["namespace"]
    release = args.release or args.key

    cmd = ["helm", "rollback", release]
    # If revision is omitted, Helm rolls back to previous revision. [web:641]
    if args.revision is not None:
        cmd.append(str(args.revision))

    cmd += ["-n", ns]

    if args.wait:
        cmd.append("--wait")
    if args.timeout:
        cmd += ["--timeout", args.timeout]

    print(f"Rolling back {tool['name']} (release={release}) in namespace '{ns}'...\n")
    run_cmd(cmd, dry_run=args.dry_run)


def register_history_command(subparsers):
    p = subparsers.add_parser("history", help="Show Helm history for a tool")
    p.add_argument("key", help="Tool key, e.g. prometheus")
    p.add_argument("--namespace", help="Override namespace from registry")
    p.add_argument("--release", help="Override Helm release name (default: same as key)")
    p.add_argument("--max", type=int, default=10, help="Show last N revisions (default: 10)")
    p.add_argument("--json", action="store_true", help="Print raw JSON from helm history")
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    p.set_defaults(func=cmd_history)


def register_rollback_command(subparsers):
    p = subparsers.add_parser("rollback", help="Rollback a Helm release for a tool")
    p.add_argument("key", help="Tool key, e.g. prometheus")
    p.add_argument("--revision", type=int, help="Revision number (omit to rollback to previous)")
    p.add_argument("--namespace", help="Override namespace from registry")
    p.add_argument("--release", help="Override Helm release name (default: same as key)")
    p.add_argument("--wait", action="store_true", help="Wait for resources to become ready")
    p.add_argument("--timeout", help="Helm timeout (e.g. 5m, 2m30s)")
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    p.set_defaults(func=cmd_rollback)
