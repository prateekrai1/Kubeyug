import json
from kubeyug.registry import find_tool
from kubeyug.helm_ops import helm_status


def cmd_status(args):
    found = find_tool(args.key)
    if not found:
        raise SystemExit(f"Unknown tool key: {args.key}")

    _, tool = found
    ns = args.namespace or tool["namespace"]

    out = helm_status(args.key, ns, dry_run=args.dry_run)
    if args.json:
        print(out if out else "{}")
    else:
        # keep it simple for now
        if out:
            obj = json.loads(out)
            print(f"Release: {obj.get('name')}  Namespace: {obj.get('namespace')}  Status: {obj.get('info', {}).get('status')}")
        else:
            print("dry-run: helm status not executed")


def register_status_command(subparsers):
    p = subparsers.add_parser("status", help="Show Helm status for a tool key")
    p.add_argument("key", help="tool key, e.g. prometheus")
    p.add_argument("--namespace", help="Override namespace from registry")
    p.add_argument("--json", action="store_true", help="Print raw JSON from helm status")
    p.add_argument("--dry-run", action="store_true", help="Print command without executing")
    p.set_defaults(func=cmd_status)
