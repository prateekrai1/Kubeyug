from kubeyug.registry import list_registry_tools
from kubeyug.helm_ops import helm_list


def cmd_list(args):
    tools = list_registry_tools()

    if args.full:
        import json
        print("Registry tools:")
        print(json.dumps(tools, indent=2))
    else:
        for t in tools:
            print(f"{t.get('category')}/{t.get('key')}: {t.get('name')}")

    if args.helm:
        print("\nHelm releases:")
        out = helm_list(namespace=args.namespace, dry_run=args.dry_run)
        print(out if out else "[]")


def register_list_command(subparsers):
    p = subparsers.add_parser("list", help="List registry tools (and optionally Helm releases)")
    p.add_argument("--full", action="store_true", help="Print full registry JSON (slow)")
    p.add_argument("--helm", action="store_true", help="Also show helm releases")
    p.add_argument("--namespace", help="Filter helm list to a namespace (default: all)")
    p.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    p.set_defaults(func=cmd_list)
