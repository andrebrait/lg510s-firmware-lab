"""Run allowlisted read-only commands at LG510S U-Boot; leave the board at the U-Boot prompt.

Usage: uboot_probe.py CMD [CMD ...]   (use the literal arg 'reset' last to boot stock firmware)
If the prompt is not already present, waits for a power cycle and interrupts autoboot.
"""
import os, re, sys, termios, time, select

DEV = os.environ.get('LG510S_TTY', '/dev/cu.usbserial-XXXX')
LOG = os.path.expanduser('~/lg510s-dump/uart/uboot-session.log')
PROMPT = b'RTL9300# '
SAFE = re.compile(r'^(version|flshow|flinfo|help( \w+)?|iminfo [0-9a-fx]+|md(\.[bwl])? [0-9a-fx]+( [0-9a-fx]+)?'
                  r'|crc32 [0-9a-fx]+ [0-9a-fx]+|rtk show hw_profile_list|rtk boardmodel|rtk boardid'
                  r'|rtk pinGet [0-7]|rtk phyreg get \d+ \d+ \d+|rtk phymmd get \d+ \d+ \d+( \d+)?|rtk sdsreg get \d+ \d+ \d+( \d+)?'
                  r'|rtk unit get|rtk network on|rtk network off|mw\.l bb00cb7[048c] [0-9a-f]{1,8}|rtk sdsreg set 0 5 \d+ \d+ 0x[0-9a-f]{4}'
                  r'|rtk i2c init sw( \d+){10}|rtk i2c read \d+ \d+|rtk phymmd set 0 \d+ 30 323 0x[0-9a-f]{4}|sleep \d+'
                  r'|setenv (ipaddr|netmask|serverip) [\d.]+|ping [\d.]+|printenv autostart'
                  r'|mw\.l bb00cc[0-4][048c] [0-9a-f]{8}'
                  r'|tftpboot 8[1-7][0-9a-f]{6} [\w.-]+|iminfo 8[1-7][0-9a-f]{6}|bootm 8[4-7][0-9a-f]{6}|boota|reset)$')
cmds = sys.argv[1:]
bad = [c for c in cmds if not SAFE.match(c)]
assert not bad, f'refusing non-allowlisted commands: {bad}'
assert 'reset' not in cmds[:-1], 'reset only as last command'

fd = os.open(DEV, os.O_RDWR | os.O_NOCTTY)
a = termios.tcgetattr(fd)
a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
a[4] = a[5] = termios.B115200
a[6][termios.VMIN] = 0; a[6][termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, a)
termios.tcflush(fd, termios.TCIOFLUSH)
log = open(LOG, 'ab')
buf = bytearray()

def pump(t):
    r, _, _ = select.select([fd], [], [], t)
    if r:
        d = os.read(fd, 4096)
        buf.extend(d); log.write(d); log.flush()
        sys.stdout.write(d.decode('latin-1')); sys.stdout.flush()

def wait_for(pat, timeout, esc=False):
    start = len(buf); end = time.time() + timeout
    while time.time() < end:
        pump(0.05)
        if esc:
            os.write(fd, b'\x1b')
        if pat in buf[start:]:
            return True
    return False

def send(cmd):
    for ch in cmd.encode() + b'\r':
        os.write(fd, bytes([ch])); time.sleep(0.005)

send('')
if not wait_for(PROMPT, 2):
    print('\nREADY: power the switch on now', flush=True)
    if not wait_for(b'Hit Esc key', 3600):
        sys.exit('no U-Boot banner within 3600 s')
    if not wait_for(PROMPT, 5, esc=True):
        sys.exit('missed autoboot window; stock boot continues, nothing sent')
    time.sleep(0.5); pump(0.3)          # drain echo of extra Esc bytes
    send('')
    assert wait_for(PROMPT, 3), 'no clean prompt after interrupt'
for c in cmds:
    send(c)
    if c == 'reset':
        wait_for(b'Starting kernel', 60)
        break
    if not wait_for(PROMPT, 30):
        sys.exit(f'no prompt after {c!r}; stopping')
print('\nDONE', flush=True)
