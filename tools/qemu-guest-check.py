#!/usr/bin/env python3
"""Check the pinned Linux prototype inside the disposable Malta guest, never a switch."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import socket
import subprocess
import tarfile
import tempfile
import time

RUN = "/run/rtlp-bench-fullsystem"
APP = "/tmp/rtlp-qemu"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("prototype", type=Path)
    parser.add_argument("identity", type=Path)
    parser.add_argument("known_hosts", type=Path)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    if args.report.exists():
        parser.error("report already exists; use a new path")
    ssh = ["ssh", "-p", "22044", "-i", str(args.identity), "-o", "IdentityAgent=none",
           "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes",
           "-o", "UserKnownHostsFile=" + str(args.known_hosts), "-o", "ConnectTimeout=10", "root@127.0.0.1"]
    checks = []
    failures = []
    complete = False

    def guest(command, data=None, allowed=(0,)):
        p = subprocess.run(ssh + [command], input=data, capture_output=True, timeout=45)
        if p.returncode not in allowed:
            raise RuntimeError(f"guest command failed ({p.returncode}): {command}\n{p.stderr.decode(errors='replace')}")
        return p.returncode, p.stdout.decode(errors="replace")

    def check(name, condition):
        if condition:
            checks.append(name)
            print("PASS " + name, flush=True)
        else:
            failures.append(name)
            print("FAIL " + name, flush=True)

    def cli(command):
        _, out = guest(f"{APP}/swcli -s {RUN}/cli.sock", (command + "\n").encode())
        if "Error:" in out:
            name = "CLI " + command.split()[0] + " rejects a valid operation: " + out.strip()
            failures.append(name)
            print("FAIL " + name, flush=True)
        return out

    def start():
        guest(f"ip netns exec rtlp-sw {APP}/rtlplayground --http 0.0.0.0:18080 "
              f"--cli-socket {RUN}/cli.sock --cfg-dir {RUN}/cfg --www {APP}/www "
              f"--dhcp-script {APP}/udhcpc.script </dev/null >{RUN}/console.log 2>{RUN}/daemon.log & "
              f"echo $! >{RUN}/pid")
        guest(f"for n in 1 2 3 4 5 6 7 8 9 10; do [ -S {RUN}/cli.sock ] && exit 0; sleep 1; done; exit 1")

    def ping(host, address):
        code, _ = guest(f"ip netns exec rtlp-h{host} ping -c 2 -W 1 {address}", allowed=(0, 1))
        return code == 0

    model = guest("cat /proc/cpuinfo")[1]
    check("refuse any machine other than the emulated Malta", "malta" in model.lower())
    check("actual reference userspace is running", "r0-19483fa" in guest("cat /etc/openwrt_release")[1])
    if failures:
        raise RuntimeError("refusing to modify a non-validation guest")
    guest(f"test ! -e {APP}; mkdir {APP}")
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w:gz") as tar:
        for name in ("rtlplayground", "swcli"):
            tar.add(args.prototype / "platform/linux/output/mips" / name, arcname=name, recursive=False)
        tar.add(args.prototype / "platform/linux/udhcpc.script", arcname="udhcpc.script", recursive=False)
        for name in ("setup.sh", "teardown.sh"):
            tar.add(args.prototype / "platform/linux/bench" / name, arcname="bench/" + name, recursive=False)
        for file in sorted((args.prototype / "output/html_min").iterdir()):
            if file.is_file():
                tar.add(file, arcname="www/" + file.name, recursive=False)
    guest(f"tar -xz -C {APP}", archive.getvalue())
    owned = False
    tunnel = None
    try:
        guest(f"RTLP_BENCH_RUN={RUN} sh {APP}/bench/setup.sh")
        owned = True
        # Host 6 becomes the SSH guest's HTTP client; requests still enter swbr through lan6.
        guest("ip -n rtlp-h6 link set h6 netns 1; ip addr replace 192.0.2.16/24 dev h6; ip link set h6 up")
        start()
        cli("ip 192.0.2.10")
        cli("netmask 255.255.255.0")
        # Test the broken CLI path honestly, then establish an independent network fixture.
        addresses = json.loads(guest("ip -n rtlp-sw -j -4 addr show dev swbr")[1])
        check("CLI sets the requested IPv4 address and prefix", any(
            a.get("local") == "192.0.2.10" and a.get("prefixlen") == 24
            for link in addresses for a in link.get("addr_info", [])))
        guest("ip -n rtlp-sw -4 addr flush dev swbr; ip -n rtlp-sw addr add 192.0.2.10/24 dev swbr")
        cli("passwd qemu-validation-pass")
        check("untagged forwarding between virtual ports", ping(1, "192.0.2.12"))
        with tempfile.TemporaryDirectory(prefix="qemu-http-", dir=args.report.parent) as tmp:
            tmp = Path(tmp)
            with (tmp / "tunnel.log").open("wb") as log:
                tunnel = subprocess.Popen(ssh[:-1] + ["-o", "ExitOnForwardFailure=yes", "-N", "-L",
                    "127.0.0.1:18084:192.0.2.10:18080", ssh[-1]], stdout=subprocess.DEVNULL, stderr=log)
            deadline = time.monotonic() + 10
            while True:
                if tunnel.poll() is not None:
                    raise RuntimeError((tmp / "tunnel.log").read_text())
                try:
                    with socket.create_connection(("127.0.0.1", 18084), timeout=1):
                        break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(0.1)

            def http(path, data=None, cookies=True, form=False):
                cmd = ["curl", "--silent", "--show-error", "--compressed", "--path-as-is", "--max-time", "15",
                       "--max-redirs", "0", "-o", str(tmp / "body"), "-D", str(tmp / "headers"), "-w", "%{http_code}"]
                if cookies:
                    cmd += ["-b", str(tmp / "cookies"), "-c", str(tmp / "cookies")]
                if data is not None:
                    cmd += ["--data-urlencode" if form else "--data-binary", data]
                result = subprocess.run(cmd + ["http://127.0.0.1:18084/" + path], capture_output=True, text=True, timeout=20)
                if result.returncode:
                    raise RuntimeError(result.stderr)
                return int(result.stdout), (tmp / "body").read_bytes(), (tmp / "headers").read_text()

            for attempt in range(10):
                try:
                    if http("login.html", cookies=False)[0] == 200:
                        break
                except RuntimeError:
                    pass
                time.sleep(0.5)
            check("unauthenticated JSON is refused", http("status.json", cookies=False)[0] == 401)
            code, _, headers = http("login", "pwd=wrong", form=True)
            check("wrong password gives no session", code == 302 and "Set-Cookie:" not in headers)
            time.sleep(1.1)
            code, _, headers = http("login", "pwd=qemu-validation-pass", form=True)
            check("MIPS password hashing and authenticated HTTP login", code == 302 and "Set-Cookie: session=" in headers)
            code, body, _ = http("status.json")
            status = json.loads(body)
            check("six 10G virtual links reported correctly", code == 200 and len(status) == 6 and all(p["link"] == 5 for p in status))
            guest("ip -n rtlp-h3 link set h3 down")
            check("link-down is visible through HTTP", json.loads(http("status.json")[1])[2]["link"] == 0)
            guest("ip -n rtlp-h3 link set h3 up")
            check("link recovery is visible through HTTP", json.loads(http("status.json")[1])[2]["link"] == 5)
            code, body, headers = http("app.js")
            check("authenticated gzip web asset is intact", code == 200 and "Content-Encoding: gzip" in headers and
                  hashlib.sha256(body).digest() == hashlib.sha256((args.prototype / "output/html_min/app.js").read_bytes()).digest())
            for path in ("information.json", "mtu.json", "vlanlist", "vlan.json?vid=1", "counters.json?port=1", "l2.json?idx=0"):
                code, body, _ = http(path)
                json.loads(body)
                check("MIPS JSON endpoint " + path, code == 200)
            check("path traversal is refused", http("../../Makefile")[0] == 404)
            check("invalid port is refused", http("counters.json?port=99")[0] == 400)
            check("HTTP command changes backend state", http("cmd", "hostname qemu-be")[0] == 200 and
                  json.loads(http("information.json")[1])["hostname"] == "qemu-be")
            info = json.loads(http("information.json")[1])
            check("IPv4 address and mask are rendered correctly", info["ip_address"] == "192.0.2.10"
                  and info["ip_netmask"] == "255.255.255.0")
            cli("mtu 2 9000")
            check("MTU command reaches kernel netdev",
                  guest("ip netns exec rtlp-sw cat /sys/class/net/lan2/mtu")[1].strip() == "8974")
            cli("mtu 2 1526")
            guest("ip -n rtlp-h1 addr add 198.51.100.1/24 dev h1; "
                  "ip -n rtlp-h2 link add link h2 name h2.10 type vlan id 10; "
                  "ip -n rtlp-h2 addr add 198.51.100.2/24 dev h2.10; ip -n rtlp-h2 link set h2.10 up; "
                  "ip -n rtlp-h3 addr add 198.51.100.3/24 dev h3")
            cli("vlan 1 2 3 4 5 6")
            cli("vlan 10 lab 1 2t")
            cli("pvid 1 10")
            check("untagged to tagged VLAN forwarding", ping(1, "198.51.100.2"))
            check("tagged to untagged VLAN forwarding", ping(2, "198.51.100.1"))
            check("other VLAN cannot reach untagged host", not ping(3, "198.51.100.1"))
            check("other VLAN cannot reach tagged host", not ping(3, "198.51.100.2"))
            check("VLAN API reflects kernel-backed configuration", json.loads(http("vlan.json?vid=10")[1]) ==
                  {"members": "0x2000603", "name": "lab", "pvid": "0x0001"})
            mac = guest("ip netns exec rtlp-h2 cat /sys/class/net/h2/address")[1].strip().lower()
            rows = json.loads(http("l2.json?idx=0")[1])
            check("learned MAC and VLAN survive MIPS FDB decoding", any(e["mac"].lower() == mac and
                  int(e["vlan"], 16) == 10 and int(e["port"]) == 1 for e in rows))
            check("old management VLAN is isolated from host 1", not ping(1, "192.0.2.10"))
            cli("vlan 10 mgmt")
            check("management follows selected VLAN", ping(1, "192.0.2.10"))
            check("previous VLAN loses management access", not ping(3, "192.0.2.10"))
            cli("vlan 1 mgmt")
            # This prototype saves through POST /config, not a CLI "save" command.
            config = tmp / "startup.txt"
            config.write_text("hostname qemu-be\npasswd qemu-validation-pass\n"
                              "vlan 1 2 3 4 5 6\nvlan 10 lab 1 2t\npvid 1 10\nvlan 1 mgmt\n")
            saved = subprocess.run(["curl", "--silent", "--show-error", "--max-time", "15",
                "-b", str(tmp / "cookies"), "-F", "uploadedfile=@" + str(config),
                "-o", str(tmp / "save-body"), "-w", "%{http_code}",
                "http://127.0.0.1:18084/config"], capture_output=True, text=True, timeout=20)
            check("configuration upload is accepted", saved.returncode == 0 and saved.stdout == "200")
            code, _ = guest(f"grep -q qemu-validation-pass {RUN}/cfg/startup-config", allowed=(0, 1))
            check("stored configuration contains no plaintext password", code == 1)
            guest(f"kill -TERM $(cat {RUN}/pid); for n in 1 2 3 4 5; do "
                  f"kill -0 $(cat {RUN}/pid) 2>/dev/null || exit 0; sleep 1; done; exit 1")
            start()
            # IPv4 persistence is blocked by the recorded endian bug; restore only the fixture address.
            cli("ip 0.0.0.0")
            guest("ip -n rtlp-sw -4 addr flush dev swbr; ip -n rtlp-sw addr add 192.0.2.10/24 dev swbr")
            check("restart invalidates old HTTP session", http("status.json")[0] == 401)
            http("login", "pwd=qemu-validation-pass", form=True)
            check("saved hostname survives process restart", json.loads(http("information.json")[1])["hostname"] == "qemu-be")
            check("saved VLAN survives process restart", any(v["id"] == 10 for v in json.loads(http("vlanlist")[1])["vlan"]))
            complete = True
    finally:
        if tunnel is not None:
            tunnel.terminate()
            try:
                tunnel.wait(timeout=5)
            except subprocess.TimeoutExpired:
                tunnel.kill()
                tunnel.wait()
        if owned:
            _, out = guest(f"cat {RUN}/daemon.log", allowed=(0, 1))
            args.report.with_suffix(".daemon.log").write_text(out)
            guest(f"RTLP_BENCH_RUN={RUN} sh {APP}/bench/teardown.sh")
        guest(f"rm -r {APP}")
        with args.report.open("x") as report:
            json.dump({"complete": complete, "all_passed": complete and not failures,
                       "checks_passed": checks, "checks_failed": failures, "hardware_tested": False}, report, indent=2)
            report.write("\n")
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
