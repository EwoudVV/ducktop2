.syntax unified
.cpu cortex-m4
.fpu fpv4-sp-d16
.thumb

.global g_pfnVectors
.global Default_Handler

.word _estack

.section .isr_vector, "a", %progbits
.type g_pfnVectors, %object
g_pfnVectors:
    .word _estack
    .word Reset_Handler
    .word NMI_Handler
    .word HardFault_Handler
    .word MemManage_Handler
    .word BusFault_Handler
    .word UsageFault_Handler
    .word 0
    .word 0
    .word 0
    .word 0
    .word SVC_Handler
    .word DebugMon_Handler
    .word 0
    .word PendSV_Handler
    .word SysTick_Handler

    /* External Interrupts */
    .word WWDG_IRQHandler
    .word PVD_IRQHandler
    .word TAMP_STAMP_IRQHandler
    .word RTC_WKUP_IRQHandler
    .word FLASH_IRQHandler
    .word RCC_IRQHandler
    .word EXTI0_IRQHandler
    .word EXTI1_IRQHandler
    .word EXTI2_IRQHandler
    .word EXTI3_IRQHandler
    .word EXTI4_IRQHandler
    .word DMA1_Stream0_IRQHandler
    .word DMA1_Stream1_IRQHandler
    .word DMA1_Stream2_IRQHandler
    .word DMA1_Stream3_IRQHandler
    .word DMA1_Stream4_IRQHandler
    .word DMA1_Stream5_IRQHandler
    .word DMA1_Stream6_IRQHandler
    .word ADC_IRQHandler
    .word CAN1_TX_IRQHandler
    .word CAN1_RX0_IRQHandler
    .word CAN1_RX1_IRQHandler
    .word CAN1_SCE_IRQHandler
    .word EXTI9_5_IRQHandler
    .word TIM1_BRK_TIM9_IRQHandler
    .word TIM1_UP_TIM10_IRQHandler
    .word TIM1_TRG_COM_TIM11_IRQHandler
    .word TIM1_CC_IRQHandler
    .word TIM2_IRQHandler
    .word TIM3_IRQHandler
    .word TIM4_IRQHandler
    .word I2C1_EV_IRQHandler
    .word I2C1_ER_IRQHandler
    .word I2C2_EV_IRQHandler
    .word I2C2_ER_IRQHandler
    .word SPI1_IRQHandler
    .word SPI2_IRQHandler
    .word USART1_IRQHandler
    .word USART2_IRQHandler
    .word USART3_IRQHandler
    .word EXTI15_10_IRQHandler
    .word RTC_Alarm_IRQHandler
    .word OTG_FS_WKUP_IRQHandler
    .word TIM8_BRK_TIM12_IRQHandler
    .word TIM8_UP_TIM13_IRQHandler
    .word TIM8_TRG_COM_TIM14_IRQHandler
    .word TIM8_CC_IRQHandler
    .word DMA1_Stream7_IRQHandler
    .word FSMC_IRQHandler
    .word SDIO_IRQHandler
    .word TIM5_IRQHandler
    .word SPI3_IRQHandler
    .word UART4_IRQHandler
    .word UART5_IRQHandler
    .word TIM6_DAC_IRQHandler
    .word TIM7_IRQHandler
    .word DMA2_Stream0_IRQHandler
    .word DMA2_Stream1_IRQHandler
    .word DMA2_Stream2_IRQHandler
    .word DMA2_Stream3_IRQHandler
    .word DMA2_Stream4_IRQHandler
    .word CAN2_TX_IRQHandler
    .word CAN2_RX0_IRQHandler
    .word CAN2_RX1_IRQHandler
    .word CAN2_SCE_IRQHandler
    .word OTG_FS_IRQHandler
    .word DMA2_Stream5_IRQHandler
    .word DMA2_Stream6_IRQHandler
    .word DMA2_Stream7_IRQHandler
    .word USART6_IRQHandler
    .word I2C3_EV_IRQHandler
    .word I2C3_ER_IRQHandler
    .word OTG_HS_EP1_OUT_IRQHandler
    .word OTG_HS_EP1_IN_IRQHandler
    .word OTG_HS_WKUP_IRQHandler
    .word OTG_HS_IRQHandler
    .word DCMI_IRQHandler
    .word FPU_IRQHandler
    .word 0
    .word 0
    .word SPI4_IRQHandler
    .word 0
    .word 0
    .word SAI1_IRQHandler
    .word 0
    .word 0
    .word 0
    .word TAMP_STAMP_IRQHandler_LC
    .word RTC_WKUP_IRQHandler_LC
    .word 0
    .word 0
    .word 0
    .word 0
    .word I2C4_EV_IRQHandler
    .word I2C4_ER_IRQHandler
    .word SPDIF_RX_IRQHandler
g_pfnVectors_end:
.size g_pfnVectors, . - g_pfnVectors

.text
.thumb_func
.type Reset_Handler, %function
Reset_Handler:
    ldr r0, =_sdata
    ldr r1, =_sidata
    ldr r2, =_edata
    subs r2, r0
    ble .L0
    bl memcpy

.L0:
    ldr r0, =_sbss
    ldr r2, =_ebss
    subs r2, r0
    ble .L1
    movs r1, 0
    bl memset

.L1:
    mov r0, 0
    bl SystemInit
    bl main
    b .

.thumb_func
.type Default_Handler, %function
Default_Handler:
    b .

.macro irq_handler name
.thumb_func
.type \name, %function
.weak \name
\name:
    b Default_Handler
.endm

irq_handler NMI_Handler
irq_handler HardFault_Handler
irq_handler MemManage_Handler
irq_handler BusFault_Handler
irq_handler UsageFault_Handler
irq_handler SVC_Handler
irq_handler DebugMon_Handler
irq_handler PendSV_Handler
irq_handler SysTick_Handler

irq_handler WWDG_IRQHandler
irq_handler PVD_IRQHandler
irq_handler TAMP_STAMP_IRQHandler
irq_handler RTC_WKUP_IRQHandler
irq_handler FLASH_IRQHandler
irq_handler RCC_IRQHandler
irq_handler EXTI0_IRQHandler
irq_handler EXTI1_IRQHandler
irq_handler EXTI2_IRQHandler
irq_handler EXTI3_IRQHandler
irq_handler EXTI4_IRQHandler
irq_handler DMA1_Stream0_IRQHandler
irq_handler DMA1_Stream1_IRQHandler
irq_handler DMA1_Stream2_IRQHandler
irq_handler DMA1_Stream3_IRQHandler
irq_handler DMA1_Stream4_IRQHandler
irq_handler DMA1_Stream5_IRQHandler
irq_handler DMA1_Stream6_IRQHandler
irq_handler ADC_IRQHandler
irq_handler CAN1_TX_IRQHandler
irq_handler CAN1_RX0_IRQHandler
irq_handler CAN1_RX1_IRQHandler
irq_handler CAN1_SCE_IRQHandler
irq_handler EXTI9_5_IRQHandler
irq_handler TIM1_BRK_TIM9_IRQHandler
irq_handler TIM1_UP_TIM10_IRQHandler
irq_handler TIM1_TRG_COM_TIM11_IRQHandler
irq_handler TIM1_CC_IRQHandler
irq_handler TIM2_IRQHandler
irq_handler TIM3_IRQHandler
irq_handler TIM4_IRQHandler
irq_handler I2C1_EV_IRQHandler
irq_handler I2C1_ER_IRQHandler
irq_handler I2C2_EV_IRQHandler
irq_handler I2C2_ER_IRQHandler
irq_handler SPI1_IRQHandler
irq_handler SPI2_IRQHandler
irq_handler USART1_IRQHandler
irq_handler USART2_IRQHandler
irq_handler USART3_IRQHandler
irq_handler EXTI15_10_IRQHandler
irq_handler RTC_Alarm_IRQHandler
irq_handler OTG_FS_WKUP_IRQHandler
irq_handler TIM8_BRK_TIM12_IRQHandler
irq_handler TIM8_UP_TIM13_IRQHandler
irq_handler TIM8_TRG_COM_TIM14_IRQHandler
irq_handler TIM8_CC_IRQHandler
irq_handler DMA1_Stream7_IRQHandler
irq_handler FSMC_IRQHandler
irq_handler SDIO_IRQHandler
irq_handler TIM5_IRQHandler
irq_handler SPI3_IRQHandler
irq_handler UART4_IRQHandler
irq_handler UART5_IRQHandler
irq_handler TIM6_DAC_IRQHandler
irq_handler TIM7_IRQHandler
irq_handler DMA2_Stream0_IRQHandler
irq_handler DMA2_Stream1_IRQHandler
irq_handler DMA2_Stream2_IRQHandler
irq_handler DMA2_Stream3_IRQHandler
irq_handler DMA2_Stream4_IRQHandler
irq_handler CAN2_TX_IRQHandler
irq_handler CAN2_RX0_IRQHandler
irq_handler CAN2_RX1_IRQHandler
irq_handler CAN2_SCE_IRQHandler
irq_handler OTG_FS_IRQHandler
irq_handler DMA2_Stream5_IRQHandler
irq_handler DMA2_Stream6_IRQHandler
irq_handler DMA2_Stream7_IRQHandler
irq_handler USART6_IRQHandler
irq_handler I2C3_EV_IRQHandler
irq_handler I2C3_ER_IRQHandler
irq_handler OTG_HS_EP1_OUT_IRQHandler
irq_handler OTG_HS_EP1_IN_IRQHandler
irq_handler OTG_HS_WKUP_IRQHandler
irq_handler OTG_HS_IRQHandler
irq_handler DCMI_IRQHandler
irq_handler FPU_IRQHandler
irq_handler SPI4_IRQHandler
irq_handler SAI1_IRQHandler
irq_handler TAMP_STAMP_IRQHandler_LC
irq_handler RTC_WKUP_IRQHandler_LC
irq_handler I2C4_EV_IRQHandler
irq_handler I2C4_ER_IRQHandler
irq_handler SPDIF_RX_IRQHandler

.end
