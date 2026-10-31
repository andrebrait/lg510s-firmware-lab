/* Network-order storage must be identical on the native and MIPS builds. */
/* Match cmd_parser.c's include environment, not the libc networking headers. */
#include "platform.h"
#include "uip/uip.h"
#include <stdio.h>
#include <string.h>

static int expect(const char *name, const uip_ipaddr_t *address, const uint8_t expected[4])
{
    const uint8_t *actual = (const uint8_t *)address;
    int failed = memcmp(actual, expected, 4) != 0;
    printf("%s %s: expected %u.%u.%u.%u, got %u.%u.%u.%u\n",
           failed ? "FAIL" : "PASS", name,
           expected[0], expected[1], expected[2], expected[3],
           actual[0], actual[1], actual[2], actual[3]);
    return failed;
}

int main(void)
{
    uip_ipaddr_t address, mask;
    const uint8_t expected_address[4] = {192, 0, 2, 10};
    const uint8_t expected_mask[4] = {255, 255, 255, 0};
    uip_ipaddr(&address, 192, 0, 2, 10);
    uip_ipaddr(&mask, 255, 255, 255, 0);
    int failures = expect("IPv4 storage", &address, expected_address);
    failures += expect("netmask storage", &mask, expected_mask);
    return failures != 0;
}
