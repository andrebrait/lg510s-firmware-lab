#!/usr/bin/env python3
"""Inspect a vendor startup-config or insert a global SSH service toggle offline."""
import argparse
import json
from pathlib import Path
import re

HEADER = "SYSTEM CONFIG FILE ::= BEGIN"


def checked_lines(text):
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != HEADER or "\0" in text:
        raise ValueError("not an intact vendor startup-config")
    return lines


def enable_ssh(text):
    """Preserve every unknown line; insert at global scope before any sections."""
    lines = checked_lines(text)
    newline = "\r\n" if lines[0].endswith("\r\n") else "\n"
    if not lines[0].endswith("\n"):
        lines[0] += newline
    rest = [line for line in lines[1:] if line.rstrip("\r\n") not in ("ip ssh", "no ip ssh")]
    return "".join([lines[0], "ip ssh" + newline, *rest])


def summarize(text):
    lines = checked_lines(text)
    result = {"version": None, "hostname": None, "ssh_enabled": False}
    for line in lines:
        value = line.rstrip("\r\n")
        if value.startswith("! System Version:"):
            result["version"] = value.split(":", 1)[1].strip()
        match = re.fullmatch(r'system name "([^"\r\n]*)"', value)
        if match:
            result["hostname"] = match[1]
        if value in ("ip ssh", "no ip ssh"):
            result["ssh_enabled"] = value == "ip ssh"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "enable-ssh"))
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    args = parser.parse_args()
    try:
        text = args.source.read_bytes().decode("utf-8")
        if args.action == "inspect":
            print(json.dumps(summarize(text), indent=2))
        else:
            if args.output is None:
                parser.error("enable-ssh requires a new output file")
            changed = enable_ssh(text).encode("utf-8")
            with args.output.open("xb") as target:
                args.output.chmod(0o600)
                target.write(changed)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
