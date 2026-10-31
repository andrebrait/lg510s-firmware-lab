"""Minimal read-only TFTP server (RFC 1350, octet, 512-byte blocks). Usage: tftpd.py ROOT [PORT]"""
import os, socket, struct, sys, threading

ROOT = os.path.realpath(sys.argv[1])
PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 69


def serve(peer, name):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(1.0)
    path = os.path.realpath(os.path.join(ROOT, name.lstrip('/')))
    if not path.startswith(ROOT + os.sep) or not os.path.isfile(path):
        s.sendto(struct.pack('!HH', 5, 1) + b'File not found\0', peer)
        print('miss', peer, name, flush=True)
        return
    data = open(path, 'rb').read()
    block = 1
    while True:
        chunk = data[(block - 1) * 512:block * 512]
        pkt = struct.pack('!HH', 3, block & 0xffff) + chunk
        for _ in range(10):
            s.sendto(pkt, peer)
            try:
                while True:
                    ack, addr = s.recvfrom(1024)
                    if addr == peer and ack[:2] == b'\0\4' and struct.unpack('!H', ack[2:4])[0] == block & 0xffff:
                        break
                break
            except socket.timeout:
                continue
        else:
            print('timeout', peer, name, block, flush=True)
            return
        if len(chunk) < 512:
            print('sent', peer, name, len(data), flush=True)
            return
        block += 1


srv = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
srv.bind(('0.0.0.0', PORT))
print('READY', ROOT, PORT, flush=True)
while True:
    req, peer = srv.recvfrom(1024)
    if req[:2] == b'\0\1':
        name = req[2:].split(b'\0')[0].decode(errors='replace')
        threading.Thread(target=serve, args=(peer, name), daemon=True).start()
