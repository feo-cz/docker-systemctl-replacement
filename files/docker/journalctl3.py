#! /usr/bin/env python3
#pylint: disable=multiple-statements,line-too-long,missing-module-docstring,invalid-name

import argparse
import os
import sys

def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument('-u', '--unit', metavar='unit', type=str, required=True, help='Systemd unit to display')
    parser.add_argument('-f', '--follow', default=False, action='store_true', help='Follows the log')
    parser.add_argument('-n', '--lines', metavar='num', type=int, help='Num of lines to display')
    parser.add_argument('--no-pager', default=False, action='store_true', help='Do not pipe through a pager')
    parser.add_argument('--system', default=False, action='store_true', help='Show system units')
    parser.add_argument('--user', default=False, action='store_true', help='Show user units')
    parser.add_argument('--root', metavar='path', type=str, help='Use subdirectory path')
    parser.add_argument('-x', default=False, action='store_true', help='Switch on verbose mode')
    parser.add_argument('--since', metavar='since', type=str, help='Dummy, do nothing')
    return parser

def systemctl_command(args: argparse.Namespace, path: str = "") -> list:
    """ the journalctl options are translated into a 'systemctl log' call. The tool
        is named 'systemctl' and not 'systemctl3.py' because that is how it is
        installed next to us - as the replacement of the system's own systemctl. """
    systemctl = os.path.join(path, "systemctl")
    cmd = [ systemctl, "log", args.unit ] # drops the -u
    if args.follow: cmd += [ "-f" ]
    if args.lines: cmd += [ "-n", str(args.lines) ]
    if args.no_pager: cmd += [ "--no-pager" ]
    if args.system: cmd += [ "--system" ]
    elif args.user: cmd += [ "--user" ]
    if args.root: cmd += [ "--root", args.root ]
    if args.x: cmd += [ "-vvv" ]
    return cmd

def main() -> None:
    args = argument_parser().parse_args()
    cmd = systemctl_command(args, os.path.dirname(sys.argv[0]))
    os.execvp(cmd[0], cmd)

if __name__ == "__main__":
    main()
