/* mdio IFACE PRTAD DEVAD REG [VAL] - Clause 45 PHY register access via SIOCGMIIREG/SIOCSMIIREG */
#include <linux/mii.h>
#include <linux/sockios.h>
#include <net/if.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>

int main(int argc, char **argv)
{
	struct ifreq ifr;
	struct mii_ioctl_data *mii = (struct mii_ioctl_data *)&ifr.ifr_data;
	int s;

	if (argc < 5)
		return fprintf(stderr, "usage: mdio IFACE PRTAD DEVAD REG [VAL]\n"), 2;
	s = socket(AF_INET, SOCK_DGRAM, 0);
	memset(&ifr, 0, sizeof(ifr));
	strncpy(ifr.ifr_name, argv[1], IFNAMSIZ - 1);
	mii->phy_id = 0x8000 | (strtoul(argv[2], 0, 0) << 5) | strtoul(argv[3], 0, 0);
	mii->reg_num = strtoul(argv[4], 0, 0);
	if (argc > 5) {
		mii->val_in = strtoul(argv[5], 0, 0);
		if (ioctl(s, SIOCSMIIREG, &ifr) < 0)
			return perror("SIOCSMIIREG"), 1;
	}
	if (ioctl(s, SIOCGMIIREG, &ifr) < 0)
		return perror("SIOCGMIIREG"), 1;
	printf("0x%04x\n", mii->val_out);
	return 0;
}
