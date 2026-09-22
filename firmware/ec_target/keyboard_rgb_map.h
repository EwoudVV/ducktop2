#ifndef DUCKTOP2_KEYBOARD_RGB_MAP_H
#define DUCKTOP2_KEYBOARD_RGB_MAP_H
#include <stdint.h>
#define KEYBOARD_RGB_KEYS 65u
#define KEYBOARD_RGB_CHANNELS 198u
#define KEYBOARD_RGB_BANKS 11u
#define KEYBOARD_RGB_ADDRESS 0x2fu
/* PWM register numbers, R/G/B, in the existing switch-reference order. */
static const uint8_t keyboard_rgb_map[65][3] = {
    {1u, 2u, 3u}, /* SW320 */
    {4u, 5u, 6u}, /* SW321 */
    {7u, 8u, 9u}, /* SW322 */
    {10u, 11u, 12u}, /* SW323 */
    {13u, 14u, 15u}, /* SW324 */
    {16u, 17u, 18u}, /* SW325 */
    {19u, 20u, 21u}, /* SW326 */
    {22u, 23u, 24u}, /* SW327 */
    {25u, 26u, 27u}, /* SW328 */
    {28u, 29u, 30u}, /* SW329 */
    {31u, 32u, 33u}, /* SW330 */
    {34u, 35u, 36u}, /* SW331 */
    {37u, 38u, 39u}, /* SW332 */
    {40u, 41u, 42u}, /* SW333 */
    {82u, 83u, 84u}, /* SW334 */
    {79u, 80u, 81u}, /* SW335 */
    {76u, 77u, 78u}, /* SW336 */
    {73u, 74u, 75u}, /* SW337 */
    {70u, 71u, 72u}, /* SW338 */
    {67u, 68u, 69u}, /* SW339 */
    {64u, 65u, 66u}, /* SW340 */
    {61u, 62u, 63u}, /* SW341 */
    {58u, 59u, 60u}, /* SW342 */
    {55u, 56u, 57u}, /* SW343 */
    {52u, 53u, 54u}, /* SW344 */
    {49u, 50u, 51u}, /* SW345 */
    {46u, 47u, 48u}, /* SW346 */
    {43u, 44u, 45u}, /* SW347 */
    {85u, 86u, 87u}, /* SW348 */
    {88u, 89u, 90u}, /* SW349 */
    {91u, 92u, 93u}, /* SW350 */
    {94u, 95u, 96u}, /* SW351 */
    {97u, 98u, 99u}, /* SW352 */
    {100u, 101u, 102u}, /* SW353 */
    {103u, 104u, 105u}, /* SW354 */
    {106u, 107u, 108u}, /* SW355 */
    {109u, 110u, 111u}, /* SW356 */
    {112u, 113u, 114u}, /* SW357 */
    {115u, 116u, 117u}, /* SW358 */
    {118u, 119u, 120u}, /* SW359 */
    {121u, 122u, 123u}, /* SW360 */
    {160u, 161u, 162u}, /* SW361 */
    {157u, 158u, 159u}, /* SW362 */
    {154u, 155u, 156u}, /* SW363 */
    {151u, 152u, 153u}, /* SW364 */
    {148u, 149u, 150u}, /* SW365 */
    {145u, 146u, 147u}, /* SW366 */
    {142u, 143u, 144u}, /* SW367 */
    {139u, 140u, 141u}, /* SW368 */
    {136u, 137u, 138u}, /* SW369 */
    {133u, 134u, 135u}, /* SW370 */
    {130u, 131u, 132u}, /* SW371 */
    {127u, 128u, 129u}, /* SW372 */
    {124u, 125u, 126u}, /* SW373 */
    {163u, 164u, 165u}, /* SW374 */
    {166u, 167u, 168u}, /* SW375 */
    {169u, 170u, 171u}, /* SW376 */
    {172u, 173u, 174u}, /* SW377 */
    {175u, 176u, 177u}, /* SW378 */
    {178u, 179u, 180u}, /* SW379 */
    {181u, 182u, 183u}, /* SW380 */
    {184u, 185u, 186u}, /* SW381 */
    {187u, 188u, 189u}, /* SW382 */
    {190u, 191u, 192u}, /* SW383 */
    {193u, 194u, 195u}, /* SW384 */
};
#endif
