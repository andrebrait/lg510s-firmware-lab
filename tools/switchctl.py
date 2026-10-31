#!/usr/bin/env python3
"""Small client for the observed vendor CGI API, not a general switch framework."""
import argparse
import base64
import getpass
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import tempfile
import time
from urllib.parse import urlencode


SSH_FRAGMENT = ('SYSTEM CONFIG FILE ::= BEGIN\n'
                '! System Description: KT-NOS LG510S-4T2XS Switch\n'
                '! System Version: v1.1.1.34\n!\nip ssh\n!\n')


def encode_form(fields):
    # Backbone sends a JSON object whose key contains the form-encoded payload.
    return json.dumps({"_ds=1&" + urlencode(fields) + "&_de=1": {}})


def rsa_password(password, modulus, exponent=65537):
    n = int(modulus, 16)
    size = (n.bit_length() + 7) // 8
    message = password.encode("utf-8")
    if size < 64 or size > 1024 or len(message) > size - 11:
        raise ValueError("invalid RSA key size or password too long")
    padding = bytes(secrets.randbelow(255) + 1 for _ in range(size - len(message) - 3))
    block = b"\0\x02" + padding + b"\0" + message
    ciphertext = pow(int.from_bytes(block, "big"), exponent, n)
    return base64.b64encode(ciphertext.to_bytes(size, "big")).decode("ascii")


def ssh_binding(data):
    default = [x for x in data["lists"] if x["list"] == "default"]
    if len(default) != 1 or default[0]["methods"] != ["lang('aaa','lblMethodLocal')"]:
        raise ValueError("default authentication list is not exclusively local users")
    lines = [x for x in data["lines"] if x["name"] == "lang('line','lblSsh')"]
    if len(lines) != 1 or not isinstance(lines[0]["val"], int):
        raise ValueError("cannot identify the vendor SSH line")
    return {f"list_{lines[0]['val']}": "default"}


class Client:
    def __init__(self, host, cookie_dir):
        address = ipaddress.ip_address(host)
        authority = f"[{address}]" if address.version == 6 else str(address)
        self.base = f"http://{authority}/"
        self.cookie = str(Path(cookie_dir) / "cookies")
        Path(self.cookie).touch(mode=0o600, exist_ok=False)

    def request(self, command, fields=None, query=None):
        if not re.fullmatch(r"[A-Za-z0-9_]+", command):
            raise ValueError("invalid CGI command")
        method = "get" if fields is None else "set"
        parameters = {"cmd": command, "dummy": time.time_ns(), **(query or {})}
        args = ["curl", "--silent", "--show-error", "--fail-with-body", "--max-time", "20",
                "--noproxy", "*", "--cookie", self.cookie, "--cookie-jar", self.cookie,
                self.base + f"cgi/{method}.cgi?" + urlencode(parameters)]
        payload = None
        if fields is not None:
            args += ["--header", "Content-Type: application/json", "--data-binary", "@-"]
            payload = encode_form(fields)
        result = subprocess.run(args, input=payload, text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(f"HTTP request failed for {command} (curl {result.returncode})")
        response = json.loads(result.stdout)
        if response.get("status") == "fail" or response.get("status") == "error":
            raise RuntimeError(f"vendor rejected {command}")
        return response

    def login(self, username, password):
        info = self.request("home_login")["data"]
        self.request("home_loginAuth", {"username": username,
                                      "password": rsa_password(password, info["modulus"])})
        for _ in range(10):
            status = self.request("home_loginStatus")["data"].get("status")
            if status == "ok":
                return
            if status == "fail":
                raise RuntimeError("login rejected; no password retry attempted")
            time.sleep(1)
        raise RuntimeError("login did not complete")

    def enable_ssh(self, apply, snapshot_dir):
        info = self.request("sys_sysinfo")["data"]
        identity = self.request("home_main")["data"]
        if identity.get("model") != "LG510S-4T2XS" or info.get("fwVer") != "1.1.1.34":
            raise ValueError("write workflow verified only for LG510S-4T2XS firmware 1.1.1.34")
        before = self.request("aaa_loginAuth")["data"]
        fields = ssh_binding(before)
        if not apply:
            return {"apply": False, "plan": ["bind SSH to default local-user authentication",
                    "upload a running-config fragment containing only ip ssh"],
                    "authentication_fields": fields, "flash_save": False}
        if snapshot_dir is None:
            raise ValueError("--snapshot-dir is required with --apply")
        snapshot_dir.mkdir(mode=0o700, parents=False, exist_ok=False)
        with (snapshot_dir / "aaa-before.json").open("x") as f:
            os.chmod(f.name, 0o600)
            json.dump(before, f, indent=2)
        self.request("aaa_loginAuth", fields)
        after = self.request("aaa_loginAuth")["data"]
        with (snapshot_dir / "aaa-after.json").open("x") as f:
            os.chmod(f.name, 0o600)
            json.dump(after, f, indent=2)
        ssh_id = next(iter(fields)).removeprefix("list_")
        old = {str(x['val']): x['list'] for x in before['lines']}
        new = {str(x['val']): x['list'] for x in after['lines']}
        if new.get(ssh_id) != "default" or {k:v for k,v in old.items() if k != ssh_id} != {k:v for k,v in new.items() if k != ssh_id}:
            raise RuntimeError("unexpected authentication readback; inspect private snapshots before proceeding")
        fragment = snapshot_dir / "enable-ssh.cfg"
        with fragment.open("x") as f:
            fragment.chmod(0o600)
            f.write(SSH_FRAGMENT)
        result = subprocess.run(["curl", "--silent", "--show-error", "--fail-with-body", "--max-time", "30",
                                 "--noproxy", "*", "--cookie", self.cookie, "--cookie-jar", self.cookie,
                                 "--form", "fileType=running", "--form", "cfg_action=upgrade",
                                 "--form", "method=http", "--form", f"fileName=@{fragment};type=application/octet-stream",
                                 self.base + "cgi/httpuploadruncfg.cgi"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError("running-config upload failed; SSH authentication may already be changed")
        # Do not use the startup upload endpoint or save the configuration.
        for _ in range(15):
            status = self.request("file_upStatus", query={"fileType": "running"}).get("data", {}).get("status")
            if status == "success":
                break
            if status in ("fail", "failed", "error"):
                raise RuntimeError("vendor rejected the running-config upload")
            time.sleep(1)
        else:
            raise RuntimeError("running-config upload did not finish within the observation window")
        return {"apply": True, "ssh_authentication": "default", "running_upload": "success",
                "flash_save": False, "snapshots": str(snapshot_dir)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="literal IP address; trusted LAN only (HTTP)")
    parser.add_argument("--user", default="admin")
    sub = parser.add_subparsers(dest="action", required=True)
    get = sub.add_parser("get")
    get.add_argument("command")
    enable = sub.add_parser("enable-ssh")
    enable.add_argument("--apply", action="store_true")
    enable.add_argument("--snapshot-dir", type=Path)
    args = parser.parse_args()
    try:
        password = os.environ.get("SWITCH_PASSWORD") or getpass.getpass("Switch password: ")
        with tempfile.TemporaryDirectory(prefix="lg510s-session-") as session:
            client = Client(args.host, session)
            client.login(args.user, password)
            if args.action == "get":
                response = client.request(args.command)
            else:
                response = client.enable_ssh(args.apply, args.snapshot_dir)
            print(json.dumps(response, indent=2))
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        parser.exit(1, f"error: {exc}\n")


if __name__ == "__main__":
    main()
