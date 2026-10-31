/* bpdu IFACE - print direction, protocol version and type of the first 4 BPDUs seen on IFACE. */
#include <arpa/inet.h>
#include <linux/if_packet.h>
#include <net/ethernet.h>
#include <net/if.h>
#include <stdio.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

int main(int argc, char **argv)
{
	static const unsigned char stp_dst[6] = { 0x01, 0x80, 0xc2, 0x00, 0x00, 0x00 };
	struct sockaddr_ll sll = { .sll_family = AF_PACKET, .sll_protocol = htons(ETH_P_ALL) };
	unsigned char buf[256];
	int fd, seen = 0;

	if (argc != 2 || !(sll.sll_ifindex = if_nametoindex(argv[1])))
		return 2;
	fd = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
	if (fd < 0 || bind(fd, (struct sockaddr *)&sll, sizeof(sll)) < 0)
		return perror("socket"), 1;

	alarm(20);
	while (seen < 4) {
		struct sockaddr_ll from;
		socklen_t fl = sizeof(from);
		ssize_t n = recvfrom(fd, buf, sizeof(buf), 0, (struct sockaddr *)&from, &fl);

		/* 802.3 header, LLC 42 42 03, protocol id 0000, then version and BPDU type */
		if (n < 21 || memcmp(buf, stp_dst, 6) || buf[14] != 0x42 || buf[15] != 0x42)
			continue;
		printf("%s version=%u type=0x%02x\n", from.sll_pkttype == PACKET_OUTGOING ? "tx" : "rx", buf[19], buf[20]);
		fflush(stdout);
		seen++;
	}
	return 0;
}
