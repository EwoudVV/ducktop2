/*
 * Ducktop2 EC USB HID keyboard device stack (implementation).
 * See usb_hid.h for the contract.  RM0090 section 31.
 */

#include "usb_hid.h"

#include <stddef.h>

#include "stm32f4xx.h"
#include "usb_hid_desc.h"

/* FIFO layout in words (FS core has 320 words of FIFO RAM). */
#define USB_HID_RX_FIFO_WORDS      0x40u   /* 256 bytes */
#define USB_HID_TX0_FIFO_WORDS      0x20u   /* EP0 control: 128 bytes */
#define USB_HID_TX1_FIFO_WORDS      0x20u   /* EP1 keyboard: 128 bytes */
#define USB_HID_TX2_FIFO_WORDS      0x20u   /* EP2 consumer: 128 bytes */

#define USB_HID_EP0_MAX_PACKET      64u
#define USB_HID_EP1                  1u
#define USB_HID_EP2                  2u

typedef enum {
    CTL_IDLE = 0,
    CTL_READ_DATA,      /* data stage: device -> host */
    CTL_WRITE_DATA,     /* data stage: host -> device */
    CTL_STATUS_IN,      /* status stage: device IN (ZLP) */
    CTL_STATUS_OUT,     /* status stage: host OUT (ZLP) */
} ctl_state_t;

static volatile bool s_configured = false;
static uint8_t s_device_address = 0u;
static bool s_pending_configuration = false;
static ctl_state_t s_ctl_state = CTL_IDLE;
static const uint8_t *s_ctl_data = NULL;
static uint16_t s_ctl_len = 0u;
static uint16_t s_ctl_index = 0u;
static uint8_t s_protocol = 1u;   /* boot protocol */

static volatile bool s_kb_dirty = false;
static volatile bool s_consumer_dirty = false;
static ec_hid_keyboard_report_t s_kb_shadow;
static ec_hid_consumer_report_t s_consumer_shadow;

static void ep0_arm_in(uint16_t len, const uint8_t *data)
{
    OTG_FS_IN_EP(0)->DIEPTSIZ = len | (1u << OTG_FS_DIEPTSIZ_PKTCNT_Pos);
    OTG_FS_IN_EP(0)->DIEPCTL |= OTG_FS_DIEPCTL_EPENA | OTG_FS_DIEPCTL_CNAK;
    if (len > 0u && data != NULL) {
        volatile uint32_t *fifo = OTG_FS_EP0_TXFIFO;
        uint32_t words = (uint32_t)(len + 3u) / 4u;
        uint32_t i;
        for (i = 0u; i < words; i++) {
            uint32_t word = 0u;
            uint8_t j;
            for (j = 0u; j < 4u; j++) {
                uint32_t byte_index = i * 4u + j;
                if (byte_index < len) {
                    word |= (uint32_t)data[byte_index] << (8u * j);
                }
            }
            *fifo = word;
        }
    }
}

static void ep0_arm_out(uint16_t len)
{
    /* EP0 OUT: XFRSIZ bytes, PKTCNT = ceil(len/64), 1 minimum. */
    uint32_t packets = (uint32_t)((len + USB_HID_EP0_MAX_PACKET - 1u) / USB_HID_EP0_MAX_PACKET);
    if (packets == 0u) {
        packets = 1u;
    }
    OTG_FS_OUT_EP(0)->DOEPTSIZ = len | (packets << OTG_FS_DOEPTSIZ_PKTCNT_Pos);
    OTG_FS_OUT_EP(0)->DOEPCTL |= OTG_FS_DOEPCTL_EPENA | OTG_FS_DOEPCTL_CNAK;
}

static void ep0_stall(void)
{
    OTG_FS_IN_EP(0)->DIEPCTL |= OTG_FS_DIEPCTL_STALL;
    OTG_FS_OUT_EP(0)->DOEPCTL |= OTG_FS_DOEPCTL_STALL;
}

static void ep_arm_in_endpoint(uint32_t ep, uint8_t fifo_num, const uint8_t *data, uint16_t len)
{
    OTG_IN_EP_TypeDef *in = OTG_FS_IN_EP(ep);
    in->DIEPTSIZ = (uint32_t)len | (1u << OTG_FS_DIEPTSIZ_PKTCNT_Pos);
    in->DIEPCTL |= OTG_FS_DIEPCTL_EPENA | OTG_FS_DIEPCTL_CNAK | OTG_FS_DIEPCTL_SD0PID;
    (void)fifo_num;
    volatile uint32_t *fifo = (volatile uint32_t *)(0x50001000u + (uint32_t)0x60u * 4u
                                                    + (ep == USB_HID_EP2 ? 0x20u * 4u : 0u));
    uint32_t words = (uint32_t)(len + 3u) / 4u;
    uint32_t i;
    for (i = 0u; i < words; i++) {
        uint32_t word = 0u;
        uint8_t j;
        for (j = 0u; j < 4u; j++) {
            uint32_t byte_index = i * 4u + j;
            if (byte_index < len) {
                word |= (uint32_t)data[byte_index] << (8u * j);
            }
        }
        *fifo = word;
    }
}

static void handle_setup_packet(const uint8_t *setup)
{
    uint8_t bmRequestType = setup[0];
    uint8_t bRequest = setup[1];
    uint16_t wValue = (uint16_t)setup[2] | ((uint16_t)setup[3] << 8u);
    uint16_t wIndex = (uint16_t)setup[4] | ((uint16_t)setup[5] << 8u);
    uint16_t wLength = (uint16_t)setup[6] | ((uint16_t)setup[7] << 8u);

    uint8_t direction = bmRequestType & 0x80u;
    uint8_t type = (bmRequestType >> 5u) & 0x03u;
    uint8_t recipient = bmRequestType & 0x0Fu;

    if (type == 0u) {   /* standard */
        switch (bRequest) {
        case 0x00u:     /* GET_STATUS */
            if (direction) {
                static const uint8_t status[2] = { 0x01u, 0x00u };  /* self-powered */
                s_ctl_data = status;
                s_ctl_len = 2u;
                s_ctl_index = 0u;
                s_ctl_state = CTL_READ_DATA;
                ep0_arm_in(2u, status);
            } else {
                ep0_stall();
            }
            break;

        case 0x05u:     /* SET_ADDRESS */
            s_device_address = (uint8_t)(wValue & 0x7Fu);
            s_ctl_state = CTL_STATUS_IN;
            ep0_arm_in(0u, NULL);
            break;

        case 0x06u:     /* GET_DESCRIPTOR */
            {
                uint8_t desc_type = (uint8_t)(wValue >> 8u);
                uint8_t desc_index = (uint8_t)(wValue & 0xFFu);
                const uint8_t *desc = NULL;
                uint16_t desc_len = 0u;
                switch (desc_type) {
                case USB_DT_DEVICE:
                    desc = usb_hid_device_descriptor;
                    desc_len = sizeof(usb_hid_device_descriptor);
                    break;
                case USB_DT_CONFIG:
                    desc = usb_hid_config_descriptor;
                    desc_len = sizeof(usb_hid_config_descriptor);
                    break;
                case USB_DT_STRING:
                    switch (desc_index) {
                    case 0u: desc = usb_hid_string_langid; desc_len = sizeof(usb_hid_string_langid); break;
                    case USB_STR_MANUFACTURER: desc = usb_hid_string_manufacturer; desc_len = sizeof(usb_hid_string_manufacturer); break;
                    case USB_STR_PRODUCT: desc = usb_hid_string_product; desc_len = sizeof(usb_hid_string_product); break;
                    case USB_STR_SERIAL: desc = usb_hid_string_serial; desc_len = sizeof(usb_hid_string_serial); break;
                    default: desc = NULL; break;
                    }
                    break;
                case USB_DT_HID:
                    if (wIndex == 0u) {
                        static const uint8_t hid_if0[9] = {
                            9u, USB_DT_HID, 0x11u, 0x01u, 0x00u, 0x01u,
                            USB_DT_HID_REPORT, 64u, 0x00u,
                        };
                        desc = hid_if0;
                        desc_len = sizeof(hid_if0);
                    } else if (wIndex == 1u) {
                        static const uint8_t hid_if1[9] = {
                            9u, USB_DT_HID, 0x11u, 0x01u, 0x00u, 0x01u,
                            USB_DT_HID_REPORT, 47u, 0x00u,
                        };
                        desc = hid_if1;
                        desc_len = sizeof(hid_if1);
                    }
                    break;
                case USB_DT_HID_REPORT:
                    if (wIndex == 0u) {
                        desc = usb_hid_keyboard_report_descriptor;
                        desc_len = sizeof(usb_hid_keyboard_report_descriptor);
                    } else if (wIndex == 1u) {
                        desc = usb_hid_consumer_report_descriptor;
                        desc_len = sizeof(usb_hid_consumer_report_descriptor);
                    }
                    break;
                default:
                    break;
                }
                if (desc == NULL) {
                    ep0_stall();
                    break;
                }
                if (wLength < desc_len) {
                    desc_len = wLength;
                }
                s_ctl_data = desc;
                s_ctl_len = desc_len;
                s_ctl_index = 0u;
                s_ctl_state = CTL_READ_DATA;
                ep0_arm_in(desc_len > USB_HID_EP0_MAX_PACKET ? USB_HID_EP0_MAX_PACKET : desc_len, desc);
            }
            break;

        case 0x07u:     /* SET_DESCRIPTOR */
            ep0_stall();
            break;

        case 0x08u:     /* SET_CONFIGURATION */
            s_pending_configuration = (wValue == 1u);
            s_configured = false;
            s_ctl_state = CTL_STATUS_IN;
            ep0_arm_in(0u, NULL);
            break;

        case 0x09u:     /* GET_CONFIGURATION */
            if (direction) {
                static const uint8_t config_value = 1u;
                s_ctl_data = &config_value;
                s_ctl_len = 1u;
                s_ctl_index = 0u;
                s_ctl_state = CTL_READ_DATA;
                ep0_arm_in(1u, &config_value);
            } else {
                ep0_stall();
            }
            break;

        case 0x03u:     /* SET_FEATURE */
        case 0x01u:     /* CLEAR_FEATURE */
            if (recipient == 0u) {   /* device: remote wakeup - accept, ignore */
                s_ctl_state = CTL_STATUS_IN;
                ep0_arm_in(0u, NULL);
            } else if (recipient == 2u) {   /* endpoint halt */
                uint8_t ep = (uint8_t)(wIndex & 0x7Fu);
                if (ep == 0u) {
                    ep0_stall();
                } else if (ep == USB_HID_EP1 || ep == USB_HID_EP2) {
                    if (bRequest == 0x03u) {
                        OTG_FS_IN_EP(ep)->DIEPCTL |= OTG_FS_DIEPCTL_STALL;
                    } else {
                        OTG_FS_IN_EP(ep)->DIEPCTL &= ~OTG_FS_DIEPCTL_STALL;
                    }
                    s_ctl_state = CTL_STATUS_IN;
                    ep0_arm_in(0u, NULL);
                } else {
                    ep0_stall();
                }
            } else {
                ep0_stall();
            }
            break;

        case 0x02u:     /* SET_INTERFACE */
        case 0x0Au:     /* SET_INTERFACE (alt) */
        case 0x0Bu:     /* GET_INTERFACE */
            if (bRequest == 0x0Bu && direction) {
                static const uint8_t alt = 0u;
                s_ctl_data = &alt;
                s_ctl_len = 1u;
                s_ctl_index = 0u;
                s_ctl_state = CTL_READ_DATA;
                ep0_arm_in(1u, &alt);
            } else {
                s_ctl_state = CTL_STATUS_IN;
                ep0_arm_in(0u, NULL);
            }
            break;

        default:
            ep0_stall();
            break;
        }
    } else if (type == 1u) {    /* class */
        switch (bRequest) {
        case 0x01u:     /* GET_REPORT (host reads current state) */
            if (direction) {
                if (wIndex == 0u) {
                    s_ctl_data = (const uint8_t *)&s_kb_shadow;
                    s_ctl_len = sizeof(s_kb_shadow);
                    s_ctl_index = 0u;
                    s_ctl_state = CTL_READ_DATA;
                    ep0_arm_in(sizeof(s_kb_shadow), (const uint8_t *)&s_kb_shadow);
                } else if (wIndex == 1u) {
                    s_ctl_data = (const uint8_t *)&s_consumer_shadow;
                    s_ctl_len = sizeof(s_consumer_shadow);
                    s_ctl_index = 0u;
                    s_ctl_state = CTL_READ_DATA;
                    ep0_arm_in(sizeof(s_consumer_shadow), (const uint8_t *)&s_consumer_shadow);
                } else {
                    ep0_stall();
                }
            } else {
                ep0_stall();
            }
            break;

        case 0x03u:     /* SET_IDLE */
            s_ctl_state = CTL_STATUS_IN;
            ep0_arm_in(0u, NULL);
            break;

        case 0x02u:     /* GET_IDLE */
            if (direction) {
                static const uint8_t idle = 0u;
                s_ctl_data = &idle;
                s_ctl_len = 1u;
                s_ctl_index = 0u;
                s_ctl_state = CTL_READ_DATA;
                ep0_arm_in(1u, &idle);
            } else {
                ep0_stall();
            }
            break;

        case 0x0Bu:     /* SET_PROTOCOL */
            s_protocol = (uint8_t)(wValue & 0x01u);
            s_ctl_state = CTL_STATUS_IN;
            ep0_arm_in(0u, NULL);
            break;

        case 0x0Au:     /* GET_PROTOCOL */
            if (direction) {
                s_ctl_data = &s_protocol;
                s_ctl_len = 1u;
                s_ctl_index = 0u;
                s_ctl_state = CTL_READ_DATA;
                ep0_arm_in(1u, &s_protocol);
            } else {
                ep0_stall();
            }
            break;

        default:
            ep0_stall();
            break;
        }
    } else {
        ep0_stall();
    }
}

static void enable_interrupt_endpoint(uint32_t ep, uint8_t fifo_num)
{
    OTG_IN_EP_TypeDef *in = OTG_FS_IN_EP(ep);
    in->DIEPCTL = OTG_FS_DIEPCTL_MPSIZ_8
                | OTG_FS_DIEPCTL_EPTYP_INT
                | OTG_FS_DIEPCTL_USBAEP
                | (fifo_num << OTG_FS_DIEPCTL_TXFNUM_Pos)
                | OTG_FS_DIEPCTL_SD0PID;
}

static void device_reset(void)
{
    s_configured = false;
    s_device_address = 0u;
    s_ctl_state = CTL_IDLE;
    s_ctl_data = NULL;
    s_ctl_len = 0u;
    s_ctl_index = 0u;

    OTG_FS_DEV->DCFG &= ~OTG_FS_DCFG_DAD_Msk;

    /* EP0: control, 64 bytes, enabled. */
    OTG_FS_IN_EP(0)->DIEPCTL = OTG_FS_DIEPCTL_MPSIZ_64 | OTG_FS_DIEPCTL_EPTYP_CTL | OTG_FS_DIEPCTL_USBAEP;
    OTG_FS_OUT_EP(0)->DOEPCTL = OTG_FS_DIEPCTL_MPSIZ_64 | OTG_FS_DOEPCTL_EPTYP_CTL | OTG_FS_DOEPCTL_USBAEP;

    /* Prepare EP0 OUT to receive the first SETUP packet. */
    ep0_arm_out(3u * USB_HID_EP0_MAX_PACKET);

    /* Mask endpoint interrupts for EP0 in/out. */
    OTG_FS_DEV->DAINTMSK = OTG_FS_DAINT_INEPS(0u) | OTG_FS_DAINT_OUTEPS(0u);
    OTG_FS_DEV->DIEPMSK = OTG_FS_DIEPMSK_XFRC;
    OTG_FS_DEV->DOEPMSK = OTG_FS_DOEPMSK_XFRC;

    OTG_FS_DEV->DIEPINT0 = 0xFFFFu;
    OTG_FS_OUT_EP(0)->DOEPINT = 0xFFFFu;
}

static void enumeration_done(void)
{
    /* Full-speed enumeration complete; EP0 is ready. */
    OTG_FS->GINTSTS = OTG_FS_GINT_MSK_ENUMDNE;
}

static void receive_ep0_fifo(void)
{
    OTG_CORE_TypeDef *otg = OTG_FS;
    uint8_t setup[8];
    uint32_t status = otg->GRXSTSP;
    uint32_t ep_id = status & OTG_FS_GRXSTSP_EPID_Msk;
    uint32_t packet_status = (status & OTG_FS_GRXSTSP_PKTSTS_Msk) >> OTG_FS_GRXSTSP_PKTSTS_Pos;
    uint32_t byte_count = (status & OTG_FS_GRXSTSP_BCNT_Msk) >> OTG_FS_GRXSTSP_BCNT_Pos;

    if (packet_status == 0x02u) {       /* OUT data packet */
        volatile uint32_t *fifo = (volatile uint32_t *)0x50001000u;
        uint32_t words = (byte_count + 3u) / 4u;
        uint32_t i;
        for (i = 0u; i < words; i++) {
            (void)*fifo;    /* discard: control-write data is not consumed */
        }
        if (s_ctl_state == CTL_WRITE_DATA) {
            s_ctl_state = CTL_STATUS_IN;
            ep0_arm_in(0u, NULL);
        }
    } else if (packet_status == 0x04u) {    /* SETUP transaction complete */
        /* ignore */
    } else if (packet_status == 0x06u) {    /* SETUP data received */
        volatile uint32_t *fifo = (volatile uint32_t *)0x50001000u;
        uint32_t word0 = *fifo;
        uint32_t word1 = *fifo;
        uint8_t j;
        for (j = 0u; j < 4u; j++) {
            setup[j] = (uint8_t)(word0 >> (8u * j));
        }
        for (j = 0u; j < 4u; j++) {
            setup[4u + j] = (uint8_t)(word1 >> (8u * j));
        }
        /* A new SETUP aborts any in-progress control transfer. */
        s_ctl_state = CTL_IDLE;
        handle_setup_packet(setup);
    }
    (void)ep_id;
}

static void handle_ep0_in_interrupt(void)
{
    uint32_t flags = OTG_FS_IN_EP(0)->DIEPINT;
    if (flags & OTG_FS_DIEPINT_XFRC) {
        OTG_FS_IN_EP(0)->DIEPINT = OTG_FS_DIEPINT_XFRC;
        switch (s_ctl_state) {
        case CTL_READ_DATA:
            s_ctl_index += USB_HID_EP0_MAX_PACKET;
            if (s_ctl_index < s_ctl_len) {
                uint16_t remaining = s_ctl_len - s_ctl_index;
                uint16_t chunk = remaining > USB_HID_EP0_MAX_PACKET ? USB_HID_EP0_MAX_PACKET : remaining;
                ep0_arm_in(chunk, s_ctl_data + s_ctl_index);
            } else {
                /* Data stage complete: arm OUT status stage. */
                s_ctl_state = CTL_STATUS_OUT;
                ep0_arm_out(0u);
            }
            break;
        case CTL_STATUS_IN:
            /* Status stage complete.  Apply deferred SET_ADDRESS. */
            OTG_FS_DEV->DCFG = (OTG_FS_DEV->DCFG & ~OTG_FS_DCFG_DAD_Msk)
                             | ((uint32_t)s_device_address << OTG_FS_DCFG_DAD_Pos);
            if (s_pending_configuration) {
                s_pending_configuration = false;
                enable_interrupt_endpoint(USB_HID_EP1, USB_HID_EP1);
                enable_interrupt_endpoint(USB_HID_EP2, USB_HID_EP2);
                OTG_FS_DEV->DAINTMSK |= OTG_FS_DAINT_INEPS(USB_HID_EP1)
                                      | OTG_FS_DAINT_INEPS(USB_HID_EP2);
                s_configured = true;
                s_kb_dirty = true;
                s_consumer_dirty = true;
            }
            s_ctl_state = CTL_IDLE;
            break;
        default:
            s_ctl_state = CTL_IDLE;
            break;
        }
    }
    if (flags & OTG_FS_DIEPINT_EPDISD) {
        OTG_FS_IN_EP(0)->DIEPINT = OTG_FS_DIEPINT_EPDISD;
    }
}

static void handle_ep0_out_interrupt(void)
{
    uint32_t flags = OTG_FS_OUT_EP(0)->DOEPINT;
    if (flags & OTG_FS_DOEPINT_XFRC) {
        OTG_FS_OUT_EP(0)->DOEPINT = OTG_FS_DOEPINT_XFRC;
        if (s_ctl_state == CTL_STATUS_OUT) {
            s_ctl_state = CTL_IDLE;
            if (OTG_FS_DEV->DCFG & OTG_FS_DCFG_DAD_Msk) {
                /* SET_ADDRESS already applied; re-arm EP0 OUT. */
            }
            /* Re-arm EP0 OUT for the next SETUP. */
            ep0_arm_out(3u * USB_HID_EP0_MAX_PACKET);
        } else if (s_ctl_state == CTL_WRITE_DATA) {
            s_ctl_state = CTL_STATUS_IN;
            ep0_arm_in(0u, NULL);
        } else {
            ep0_arm_out(3u * USB_HID_EP0_MAX_PACKET);
        }
    }
    if (flags & OTG_FS_DOEPINT_EPDISD) {
        OTG_FS_OUT_EP(0)->DOEPINT = OTG_FS_DOEPINT_EPDISD;
    }
}

static void try_send_report(uint32_t ep, const uint8_t *data, bool *dirty)
{
    if (!s_configured || !*dirty) {
        return;
    }
    OTG_IN_EP_TypeDef *in = OTG_FS_IN_EP(ep);
    if (in->DIEPCTL & OTG_FS_DIEPCTL_EPENA) {
        return;     /* transfer in flight; the shadow is current */
    }
    ep_arm_in_endpoint(ep, ep, data, USB_HID_REPORT_SIZE);
    *dirty = false;
}

void usb_hid_send_keyboard(const ec_hid_keyboard_report_t *report)
{
    s_kb_shadow = *report;
    s_kb_dirty = true;
}

void usb_hid_send_consumer(const ec_hid_consumer_report_t *report)
{
    s_consumer_shadow = *report;
    s_consumer_dirty = true;
}

bool usb_hid_configured(void)
{
    return s_configured;
}

void usb_hid_poll(void)
{
    OTG_CORE_TypeDef *otg = OTG_FS;
    if (!(otg->GAHBCFG & 0x01u)) {
        return;
    }
    uint32_t pending = otg->GINTSTS;
    if (pending & OTG_FS_GINT_MSK_USBRST) {
        otg->GINTSTS = OTG_FS_GINT_MSK_USBRST;
        device_reset();
    }
    if (pending & OTG_FS_GINT_MSK_ENUMDNE) {
        enumeration_done();
    }
    if (pending & OTG_FS_GINT_MSK_RXFLVL) {
        receive_ep0_fifo();
    }
    if (pending & OTG_FS_GINT_MSK_IEPINT) {
        handle_ep0_in_interrupt();
    }
    if (pending & OTG_FS_GINT_MSK_OEPINT) {
        handle_ep0_out_interrupt();
    }
    try_send_report(USB_HID_EP1, (const uint8_t *)&s_kb_shadow, (bool *)&s_kb_dirty);
    try_send_report(USB_HID_EP2, (const uint8_t *)&s_consumer_shadow, (bool *)&s_consumer_dirty);
}

void OTG_FS_IRQHandler(void)
{
    usb_hid_poll();
}

void usb_hid_init(void)
{
    OTG_CORE_TypeDef *otg = OTG_FS;

    /* 48 MHz USB clock (PLL Q=7 with 8 MHz HSE). */
    RCC->AHB1ENR |= RCC_AHB1ENR_OTGFSEN;

    /* PA11 = OTG_FS_DM, PA12 = OTG_FS_DP (AF10, AFRH bits 12..19). */
    GPIOA->MODER = (GPIOA->MODER & ~(3u << 22u) & ~(3u << 24u)) | (2u << 22u) | (2u << 24u);
    GPIOA->AFRH = (GPIOA->AFRH & ~(0xFFu << 12u)) | (0xAAu << 12u);

    /* Core soft reset. */
    otg->GRSTCTL = OTG_FS_GRSTCTL_CSRST;
    while (otg->GRSTCTL & OTG_FS_GRSTCTL_CSRST) { }

    /* FS PHY, device-only role. */
    otg->GUSBCFG = (1u << 1u) | (1u << 2u) | (1u << 16u);   /* SRPCAP, HNPCAP, PHYCLKSEL */
    otg->GCCFG = OTG_FS_GCCFG_NOVBUSSENS;                  /* self-powered, no VBUS sense */

    /* FIFO layout. */
    otg->GRXFSIZ = USB_HID_RX_FIFO_WORDS;
    otg->GNPTXFSIZ = USB_HID_TX0_FIFO_WORDS | (USB_HID_RX_FIFO_WORDS << 16u);
    otg->DIEPTXF1 = USB_HID_TX1_FIFO_WORDS
                  | ((USB_HID_RX_FIFO_WORDS + USB_HID_TX0_FIFO_WORDS) << 16u);
    otg->DIEPTXF2 = USB_HID_TX2_FIFO_WORDS
                  | ((USB_HID_RX_FIFO_WORDS + USB_HID_TX0_FIFO_WORDS + USB_HID_TX1_FIFO_WORDS) << 16u);

    /* Device mode: full speed, EP0 64 bytes. */
    OTG_FS_DEV->DCFG = OTG_FS_DCFG_DSPD_FS | OTG_FS_DCFG_EP0MPS_64;

    /* Global interrupts: reset, enumeration done, RX FIFO, suspend, EPs. */
    otg->GINTMSK = OTG_FS_GINT_MSK_USBRST | OTG_FS_GINT_MSK_ENUMDNE
                 | OTG_FS_GINT_MSK_RXFLVL | OTG_FS_GINT_MSK_USBSUSP
                 | OTG_FS_GINT_MSK_IEPINT | OTG_FS_GINT_MSK_OEPINT;

    /* Enable the OTG global interrupt line. */
    otg->GAHBCFG = 0x01u | (1u << 7u);   /* GINT + TXFELVL */

    /* NVIC: OTG_FS IRQ (IRQ 67), priority 6. */
    NVIC_ISER2 = NVIC_OTG_FS_IRQ_BIT;

    /* Soft disconnect until init completes, then connect. */
    OTG_FS_DEV->DCTL |= OTG_FS_DCTL_SDIS;
    s_configured = false;
    device_reset();
    OTG_FS_DEV->DCTL &= ~OTG_FS_DCTL_SDIS;
}
