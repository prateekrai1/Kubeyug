BANNER = r"""
 _  __ _   _ ____  _______   ___  _   _  ____ 
| |/ /| | | | __ )| ____\ \ / / | | | | |/ ___|
| ' / | | | |  _ \|  _|  \ V /| | | | | | |  _ 
| . \ | |_| | |_) | |___  | | | |_| |_| | |_| |
|_|\_\ \___/|____/|_____| |_|  \___\___/ \____|

Welcome to kubeyug!
Use kubeyug -h for help! and kubeyug list to list the commands for Kubeyug
"""


def cmd_banner(args):
    print(BANNER.rstrip("\n"))


def register_banner_command(subparsers):
    p = subparsers.add_parser("banner", help="Print the Kubeyug banner")
    p.set_defaults(func=cmd_banner)
