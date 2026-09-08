#include "stm32f4xx.h"
#include "watchdog.h"
#include <stddef.h>

/* RM0090 register maps and the STM32F407 interrupt table. */
_Static_assert(offsetof(TIM_TypeDef, BDTR) == 0x44, "TIM1 BDTR offset");
_Static_assert(offsetof(GPIO_TypeDef, AFR) == 0x20, "GPIO alternate functions");
_Static_assert(offsetof(EXTI_TypeDef, PR) == 0x14, "EXTI pending register");
_Static_assert(offsetof(ADC_TypeDef, DR) == 0x4c, "ADC data register");
_Static_assert(offsetof(USB_OTG_GlobalTypeDef, HPTXFSIZ) == 0x100, "USB host FIFO offset");
_Static_assert(offsetof(USB_OTG_GlobalTypeDef, DIEPTXF) == 0x104, "USB device FIFO offset");
_Static_assert(USB_OTG_DEVICE_BASE == 0x800, "USB device register bank");
_Static_assert(USB_OTG_IN_ENDPOINT_BASE == 0x900, "USB IN endpoint bank");
_Static_assert(USB_OTG_OUT_ENDPOINT_BASE == 0xb00, "USB OUT endpoint bank");
_Static_assert(RCC_AHB2ENR_OTGFSEN == (1u << 7), "USB FS clock gate");
_Static_assert(USB_OTG_GINTSTS_USBRST == (1u << 12), "USB bus reset interrupt");
_Static_assert(USB_OTG_DCTL_SDIS == (1u << 1), "USB soft disconnect");
_Static_assert(FLASH_ACR_ICEN == (1u << 9), "flash instruction cache");
_Static_assert(FLASH_ACR_DCEN == (1u << 10), "flash data cache");
_Static_assert(OTG_FS_IRQn == 67 && RNG_IRQn == 80 && FPU_IRQn == 81, "F407 IRQ positions");
_Static_assert(EC_WATCHDOG_DIVIDER == (4u << EC_WATCHDOG_PRESCALER_BITS), "watchdog divider");
_Static_assert((EC_WATCHDOG_RELOAD + 1u) * EC_WATCHDOG_DIVIDER == 10000u,
               "watchdog uses 10000 LSI cycles");
