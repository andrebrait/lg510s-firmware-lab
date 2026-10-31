"""Send lines to the LG510S serial console and capture output.
Usage: console.py SECONDS [LINE ...]   (each LINE sent after the previous output settles 0.5 s)"""
import os, sys, termios, time, select

DEV = os.environ.get('LG510S_TTY', '/dev/cu.usbserial-XXXX')
LOG = os.path.expanduser('~/lg510s-dump/uart/linux-session.log')
fd = os.open(DEV, os.O_RDWR | os.O_NOCTTY)
a = termios.tcgetattr(fd)
a[0] = 0; a[1] = 0; a[2] = termios.CS8 | termios.CREAD | termios.CLOCAL; a[3] = 0
a[4] = a[5] = termios.B115200
a[6][termios.VMIN] = 0; a[6][termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, a)
log = open(LOG, 'ab')


def pump(t):
    end = time.time() + t
    got = False
    while time.time() < end:
        r, _, _ = select.select([fd], [], [], 0.05)
        if r:
            d = os.read(fd, 4096)
            log.write(d); log.flush()
            sys.stdout.write(d.decode('latin-1')); sys.stdout.flush()
            got = True
            end = max(end, time.time() + 0.5)
    return got


total = float(sys.argv[1])
for line in sys.argv[2:]:
    for ch in line.encode() + b'\r':
        os.write(fd, bytes([ch])); time.sleep(0.003)
    pump(0.8)
pump(total)
