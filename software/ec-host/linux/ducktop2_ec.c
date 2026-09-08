// SPDX-License-Identifier: (GPL-2.0-only OR MIT)
/* Ducktop2 vendor HID battery and lid bridge. */
#include <linux/hid.h>
#include <linux/input.h>
#include <linux/jiffies.h>
#include <linux/module.h>
#include <linux/power_supply.h>
#include <linux/spinlock.h>
#include <linux/unaligned.h>
#include <linux/workqueue.h>

struct ducktop_ec {
    struct hid_device *hid;
    struct power_supply *battery;
    struct power_supply_desc desc;
    struct input_dev *lid;
    struct delayed_work age_work;
    spinlock_t lock;
    u8 report[64];
    unsigned long received;
    bool seen;
};
static enum power_supply_property properties[] = {
    POWER_SUPPLY_PROP_PRESENT, POWER_SUPPLY_PROP_STATUS,
    POWER_SUPPLY_PROP_CAPACITY, POWER_SUPPLY_PROP_VOLTAGE_NOW,
    POWER_SUPPLY_PROP_CURRENT_NOW, POWER_SUPPLY_PROP_CHARGE_NOW,
    POWER_SUPPLY_PROP_CHARGE_FULL, POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW,
    POWER_SUPPLY_PROP_TIME_TO_FULL_NOW,
};
static int get_property(struct power_supply *supply, enum power_supply_property prop,
                        union power_supply_propval *value)
{
    struct ducktop_ec *ec=power_supply_get_drvdata(supply);
    unsigned long irqflags;
    u8 p[64]; bool fresh;
    spin_lock_irqsave(&ec->lock,irqflags);
    memcpy(p,ec->report,sizeof(p));
    fresh=ec->seen && time_before(jiffies,ec->received+msecs_to_jiffies(2000));
    spin_unlock_irqrestore(&ec->lock,irqflags);
    u16 valid=get_unaligned_le16(p+8);
    bool present=fresh && (get_unaligned_le16(p+10)&1);
    if (prop==POWER_SUPPLY_PROP_PRESENT) { value->intval=present; return 0; }
    if (prop==POWER_SUPPLY_PROP_STATUS) {
        value->intval=POWER_SUPPLY_STATUS_UNKNOWN;
        if (!present || (valid&7)!=7) return 0;
        switch (p[13]) {
        case 2: value->intval=POWER_SUPPLY_STATUS_DISCHARGING; break;
        case 3: value->intval=POWER_SUPPLY_STATUS_CHARGING; break;
        case 4: value->intval=POWER_SUPPLY_STATUS_FULL; break;
        default: break;
        }
        return 0;
    }
    if (!present) return -ENODATA;
    switch (prop) {
    case POWER_SUPPLY_PROP_CAPACITY:
        if (!(valid&1) || p[12]>100) return -ENODATA;
        value->intval=p[12]; break;
    case POWER_SUPPLY_PROP_VOLTAGE_NOW:
        if (!(valid&2)) return -ENODATA;
        value->intval=get_unaligned_le16(p+14)*1000; break;
    case POWER_SUPPLY_PROP_CURRENT_NOW:
        if (!(valid&4)) return -ENODATA;
        value->intval=(s32)get_unaligned_le32(p+16)*1000; break;
    case POWER_SUPPLY_PROP_CHARGE_NOW:
        if (!(valid&(1<<6))) return -ENODATA;
        value->intval=get_unaligned_le32(p+20)*1000; break;
    case POWER_SUPPLY_PROP_CHARGE_FULL:
        if (!(valid&(1<<7))) return -ENODATA;
        value->intval=get_unaligned_le32(p+24)*1000; break;
    case POWER_SUPPLY_PROP_TIME_TO_EMPTY_NOW:
        if (!(valid&(1<<4))) return -ENODATA;
        value->intval=get_unaligned_le32(p+28); break;
    case POWER_SUPPLY_PROP_TIME_TO_FULL_NOW:
        if (!(valid&(1<<5))) return -ENODATA;
        value->intval=get_unaligned_le32(p+32); break;
    default: return -EINVAL;
    }
    return 0;
}
static void age_work(struct work_struct *work)
{
    struct ducktop_ec *ec=container_of(to_delayed_work(work),struct ducktop_ec,age_work);
    power_supply_changed(ec->battery);
    schedule_delayed_work(&ec->age_work,HZ);
}
static int raw_event(struct hid_device *hid, struct hid_report *report, u8 *data, int size)
{
    struct ducktop_ec *ec=hid_get_drvdata(hid);
    unsigned long flags;
    if (!ec || report->type!=HID_INPUT_REPORT || size!=64 || memcmp(data,"DT2\1",4)) return 0;
    /* Reject malformed device values before unit conversions can overflow. */
    s32 battery_ma=(s32)get_unaligned_le32(data+16);
    if (get_unaligned_le16(data+14)>20000 || battery_ma < -50000 || battery_ma > 50000 ||
        get_unaligned_le32(data+20)>100000 || get_unaligned_le32(data+24)>100000 ||
        get_unaligned_le32(data+28)>INT_MAX || get_unaligned_le32(data+32)>INT_MAX ||
        data[12]>100 || data[13]>4) return 0;
    spin_lock_irqsave(&ec->lock,flags);
    memcpy(ec->report,data,64); ec->received=jiffies; ec->seen=true;
    spin_unlock_irqrestore(&ec->lock,flags);
    if (ec->lid) {
        input_report_switch(ec->lid,SW_LID,!!(get_unaligned_le16(data+10)&2));
        input_sync(ec->lid);
    }
    if (ec->battery) power_supply_changed(ec->battery);
    return 0; /* Preserve hidraw delivery for the power-limit agent. */
}
static int probe(struct hid_device *hid, const struct hid_device_id *id)
{
    struct power_supply_config config={};
    struct ducktop_ec *ec;
    int result=hid_parse(hid);
    if (result) return result;
    if (!hid->maxcollection || hid->collection[0].usage!=0xff000001) return -ENODEV;
    ec=devm_kzalloc(&hid->dev,sizeof(*ec),GFP_KERNEL);
    if (!ec) return -ENOMEM;
    ec->hid=hid; spin_lock_init(&ec->lock); hid_set_drvdata(hid,ec);
    ec->lid=devm_input_allocate_device(&hid->dev);
    if (!ec->lid) return -ENOMEM;
    ec->lid->name="Ducktop2 lid"; ec->lid->id.bustype=BUS_USB;
    input_set_capability(ec->lid,EV_SW,SW_LID);
    result=input_register_device(ec->lid); if (result) return result;
    ec->desc.name=devm_kasprintf(&hid->dev,GFP_KERNEL,"ducktop2-%s",dev_name(&hid->dev));
    if (!ec->desc.name) return -ENOMEM;
    ec->desc.type=POWER_SUPPLY_TYPE_BATTERY; ec->desc.properties=properties;
    ec->desc.num_properties=ARRAY_SIZE(properties); ec->desc.get_property=get_property;
    config.drv_data=ec;
    ec->battery=devm_power_supply_register(&hid->dev,&ec->desc,&config);
    if (IS_ERR(ec->battery)) return PTR_ERR(ec->battery);
    result=hid_hw_start(hid,HID_CONNECT_HIDRAW); if (result) return result;
    result=hid_hw_open(hid);
    if (result) { hid_hw_stop(hid); return result; }
    INIT_DELAYED_WORK(&ec->age_work,age_work); schedule_delayed_work(&ec->age_work,HZ);
    return 0;
}
static void remove_ec(struct hid_device *hid)
{
    struct ducktop_ec *ec=hid_get_drvdata(hid);
    cancel_delayed_work_sync(&ec->age_work); hid_hw_close(hid); hid_hw_stop(hid);
}
static const struct hid_device_id ids[] = {
    { HID_USB_DEVICE(0x1209,0x2328) }, { }
};
MODULE_DEVICE_TABLE(hid,ids);
static struct hid_driver ducktop_driver={.name="ducktop2-ec",.id_table=ids,.probe=probe,.remove=remove_ec,.raw_event=raw_event};
module_hid_driver(ducktop_driver);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Ducktop2 EC battery and lid");
