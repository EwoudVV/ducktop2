#ifndef DUCKTOP2_KEYBOARD_RGB_MAP_H
#define DUCKTOP2_KEYBOARD_RGB_MAP_H
#include <stdint.h>
#define KEYBOARD_RGB_KEYS 65u
#define KEYBOARD_RGB_CHANNELS 198u
#define KEYBOARD_RGB_BANKS 11u
#define KEYBOARD_RGB_ADDRESS 0x2fu
/* PWM register numbers, R/G/B, in the existing switch-reference order. */
static const uint8_t keyboard_rgb_map[65][3] = {
    {181u, 182u, 183u}, /* SW320 */
    {16u, 17u, 18u}, /* SW321 */
    {1u, 2u, 3u}, /* SW322 */
    {19u, 20u, 21u}, /* SW323 */
    {37u, 38u, 39u}, /* SW324 */
    {55u, 56u, 57u}, /* SW325 */
    {70u, 71u, 72u}, /* SW326 */
    {73u, 74u, 75u}, /* SW327 */
    {91u, 92u, 93u}, /* SW328 */
    {109u, 110u, 111u}, /* SW329 */
    {142u, 143u, 144u}, /* SW330 */
    {127u, 128u, 129u}, /* SW331 */
    {145u, 146u, 147u}, /* SW332 */
    {163u, 164u, 165u}, /* SW333 */
    {184u, 185u, 186u}, /* SW334 */
    {4u, 5u, 6u}, /* SW335 */
    {22u, 23u, 24u}, /* SW336 */
    {34u, 35u, 36u}, /* SW337 */
    {40u, 41u, 42u}, /* SW338 */
    {58u, 59u, 60u}, /* SW339 */
    {76u, 77u, 78u}, /* SW340 */
    {106u, 107u, 108u}, /* SW341 */
    {94u, 95u, 96u}, /* SW342 */
    {112u, 113u, 114u}, /* SW343 */
    {130u, 131u, 132u}, /* SW344 */
    {148u, 149u, 150u}, /* SW345 */
    {178u, 179u, 180u}, /* SW346 */
    {166u, 167u, 168u}, /* SW347 */
    {187u, 188u, 189u}, /* SW348 */
    {7u, 8u, 9u}, /* SW349 */
    {25u, 26u, 27u}, /* SW350 */
    {43u, 44u, 45u}, /* SW351 */
    {52u, 53u, 54u}, /* SW352 */
    {61u, 62u, 63u}, /* SW353 */
    {79u, 80u, 81u}, /* SW354 */
    {97u, 98u, 99u}, /* SW355 */
    {124u, 125u, 126u}, /* SW356 */
    {115u, 116u, 117u}, /* SW357 */
    {133u, 134u, 135u}, /* SW358 */
    {151u, 152u, 153u}, /* SW359 */
    {169u, 170u, 171u}, /* SW360 */
    {190u, 191u, 192u}, /* SW361 */
    {10u, 11u, 12u}, /* SW362 */
    {28u, 29u, 30u}, /* SW363 */
    {46u, 47u, 48u}, /* SW364 */
    {64u, 65u, 66u}, /* SW365 */
    {88u, 89u, 90u}, /* SW366 */
    {82u, 83u, 84u}, /* SW367 */
    {100u, 101u, 102u}, /* SW368 */
    {118u, 119u, 120u}, /* SW369 */
    {136u, 137u, 138u}, /* SW370 */
    {160u, 161u, 162u}, /* SW371 */
    {154u, 155u, 156u}, /* SW372 */
    {172u, 173u, 174u}, /* SW373 */
    {193u, 194u, 195u}, /* SW374 */
    {13u, 14u, 15u}, /* SW375 */
    {31u, 32u, 33u}, /* SW376 */
    {49u, 50u, 51u}, /* SW377 */
    {67u, 68u, 69u}, /* SW378 */
    {85u, 86u, 87u}, /* SW379 */
    {103u, 104u, 105u}, /* SW380 */
    {121u, 122u, 123u}, /* SW381 */
    {139u, 140u, 141u}, /* SW382 */
    {157u, 158u, 159u}, /* SW383 */
    {175u, 176u, 177u}, /* SW384 */
};
#endif
