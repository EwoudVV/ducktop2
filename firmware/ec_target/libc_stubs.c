#include <stddef.h>

void *memcpy(void *dest, const void *src, size_t n)
{
    unsigned char *d = (unsigned char *)dest;
    const unsigned char *s = (const unsigned char *)src;
    size_t i;
    for (i = 0; i < n; i++) {
        d[i] = s[i];
    }
    return dest;
}

void *memset(void *s, int c, size_t n)
{
    unsigned char *p = (unsigned char *)s;
    size_t i;
    for (i = 0; i < n; i++) {
        p[i] = (unsigned char)c;
    }
    return s;
}

int memcmp(const void *s1, const void *s2, size_t n)
{
    const unsigned char *p1 = (const unsigned char *)s1;
    const unsigned char *p2 = (const unsigned char *)s2;
    size_t i;
    for (i = 0; i < n; i++) {
        if (p1[i] != p2[i]) {
            return p1[i] < p2[i] ? -1 : 1;
        }
    }
    return 0;
}

/* ARM EABI 64-bit unsigned division helper.
 * ABI: r0:r1 = quotient, r2:r3 = remainder.
 * Needed because the policy code uses uint64_t division
 * and this GCC's multilib libgcc is not found with -nostdlib. */
unsigned long long __aeabi_uldivmod(unsigned long long n, unsigned long long d)
{
    unsigned long long q = 0, r = 0;
    int i;
    if (d == 0) return 0;
    for (i = 63; i >= 0; i--) {
        r = (r << 1) | ((n >> (unsigned)i) & 1ULL);
        if (r >= d) {
            r -= d;
            q |= (1ULL << (unsigned)i);
        }
    }
    return q;
}
