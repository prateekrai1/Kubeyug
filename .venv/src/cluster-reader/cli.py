import argparse

from kubeyug.registry import load_tool_registry

from kubeyug.commands.install import register_install_command
from kubeyug.commands.status import register_status_command
from kubeyug.commands.list_cmd import register_list_command
from kubeyug.commands.uninstall import register_uninstall_command
from kubeyug.commands.rollback import register_rollback_command, register_history_command


def main():
    _ = load_tool_registry()  # validate registry early; fail fast

    parser = argparse.ArgumentParser(prog="kubeyug")
    sub = parser.add_subparsers(dest="command", required=True)

    register_install_command(sub)
    register_status_command(sub)
    register_list_command(sub)
    register_uninstall_command(sub)
    register_history_command(sub)
    register_rollback_command(sub)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
