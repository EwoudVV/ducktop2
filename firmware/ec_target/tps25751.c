#include "tps25751.h"
#include "i2c.h"
#include "board_profile.h"
#include "ducktop2/ec/ec_telemetry.h"
#include <string.h>

static uint32_t le32(const uint8_t *bytes)
{
    return (uint32_t)bytes[0] | ((uint32_t)bytes[1] << 8) |
           ((uint32_t)bytes[2] << 16) | ((uint32_t)bytes[3] << 24);
}

static bool framed_read(uint8_t address, uint8_t reg, uint8_t *data, uint8_t size)
{
    uint8_t frame[17];
    if (size > 16 || !i2c1_read(address, reg, frame, (uint16_t)(size + 1)) ||
        frame[0] != size) return false;
    memcpy(data, frame + 1, size);
    return true;
}

bool tps25751_decode_contract(const uint8_t status[5], const uint8_t pdo[6],
                              const uint8_t rdo[16], const uint8_t pd_status[4],
                              tps25751_contract_t *contract)
{
    if (!contract || !status || !pdo || !rdo || !pd_status) return false;
    memset(contract, 0, sizeof(*contract));
    uint32_t st = le32(status), pd = le32(pd_status);
    uint32_t power = le32(pdo), request = le32(rdo);
    uint8_t connection = (uint8_t)((st >> 1) & 7u);
    contract->connected = (st & 1u) != 0 && connection >= 6u;
    contract->sink = (st & (1u << 5)) == 0 && (pd & (1u << 6)) == 0;
    contract->dfp = (st & (1u << 6)) != 0;
    if (!contract->connected || !contract->sink ||
        ((st >> 20) & 3u) != 2u || ((st >> 24) & 3u) != 0u ||
        (pd & 0x0cu) == 0u || (power >> 30) != 0u || request == 0u)
        return false;

    uint16_t advertised_ma = (uint16_t)((power & 0x3ffu) * 10u);
    uint16_t operating_ma = (uint16_t)(((request >> 10) & 0x3ffu) * 10u);
    uint16_t maximum_ma = (uint16_t)((request & 0x3ffu) * 10u);
    uint8_t position = (uint8_t)(request >> 28);
    /* Only the allowed fixed sink PDOs can qualify the hardware selectors.
     * GiveBack and mismatch need different policy, so reject them here. */
    contract->voltage_mv = (uint16_t)(((power >> 10) & 0x3ffu) * 50u);
    bool voltage_allowed = contract->voltage_mv == 15000u ||
        (DUCKTOP2_PD_ALLOW_20V && contract->voltage_mv == 20000u);
    if (!voltage_allowed || position == 0u || position > 7u ||
        (request & ((1u << 27) | (1u << 26))) != 0u || operating_ma == 0u ||
        operating_ma > advertised_ma || maximum_ma != operating_ma)
        return false;
    contract->current_ma = operating_ma;
    contract->valid = true;
    return true;
}

bool tps25751_read_contract(uint8_t address, tps25751_contract_t *contract)
{
    uint8_t status[5], pdo[6], rdo[16], pd[4];
    uint8_t status_after[5], pdo_after[6], rdo_after[16], pd_after[4];
    if (!contract) return false;
    memset(contract, 0, sizeof(*contract));
    if (!framed_read(address, EC_TPS25751_STATUS_REGISTER, status, 5) ||
        !framed_read(address, EC_TPS25751_ACTIVE_PDO_REGISTER, pdo, 6) ||
        !framed_read(address, EC_TPS25751_ACTIVE_RDO_REGISTER, rdo, 16) ||
        !framed_read(address, EC_TPS25751_PD_STATUS_REGISTER, pd, 4) ||
        !framed_read(address, EC_TPS25751_STATUS_REGISTER, status_after, 5) ||
        !framed_read(address, EC_TPS25751_ACTIVE_PDO_REGISTER, pdo_after, 6) ||
        !framed_read(address, EC_TPS25751_ACTIVE_RDO_REGISTER, rdo_after, 16) ||
        !framed_read(address, EC_TPS25751_PD_STATUS_REGISTER, pd_after, 4))
        return false;
    /* No atomic snapshot exists. Two matching complete observations reject
     * a role/contract transition during the read; hardware VALID gates load. */
    if (memcmp(status, status_after, 5) || memcmp(pdo, pdo_after, 6) ||
        memcmp(rdo, rdo_after, 16) || memcmp(pd, pd_after, 4)) return false;
    return tps25751_decode_contract(status, pdo, rdo, pd, contract);
}

static bool read_port_configuration(uint8_t address,uint8_t data[18],uint8_t *length)
{
    uint8_t size,frame[19];
    /* Tool FB09.17.02 uses 17 bytes; SPMU379A additionally describes byte 18.
     * Preserve the actual controller's length and every unrelated field. */
    if (!i2c1_read(address,0x28,&size,1) || size<17u || size>18u ||
        !i2c1_read(address,0x28,frame,(uint16_t)(size+1u)) || frame[0]!=size) return false;
    memcpy(data,frame+1,size);*length=size;return true;
}

bool tps25751_set_typec_mode(uint8_t address,uint8_t mode)
{
    uint8_t data[18],after[18],length,after_length,frame[20];
    if (mode!=0u && mode!=2u) return false;
    if (!read_port_configuration(address,data,&length)) return false;
    if ((data[0]&3u)==mode) return true;
    data[0]=(uint8_t)((data[0]&~3u)|mode);
    frame[0]=0x28;frame[1]=length;memcpy(frame+2,data,length);
    if (!i2c1_write_raw(address,frame,(uint16_t)(length+2u)) ||
        !read_port_configuration(address,after,&after_length)) return false;
    return length==after_length && memcmp(data,after,length)==0;
}

static bool read_source_profile(uint8_t address,uint8_t snapshot[17])
{
    /* 0x32 is a 63-byte register. With exactly one active PDO, only the
     * three-byte header and first PDO are relevant. Read its count prefix
     * explicitly; inactive slots cannot increase the advertised count. */
    return i2c1_read(address,0x32,snapshot,8) && snapshot[0]==63u &&
           i2c1_read(address,0x29,snapshot+8,5) && snapshot[8]==4u &&
           i2c1_read(address,0x27,snapshot+13,4) &&
           snapshot[13]>=3u && snapshot[13]<=64u;
}
static bool source_profile_valid(const uint8_t snapshot[17])
{
    uint32_t pdo=le32(snapshot+4),control=le32(snapshot+9);
    const uint8_t *global=snapshot+14;
    return snapshot[1]==1u && (snapshot[2]&3u)==0u &&
           (pdo>>30)==0u && ((pdo>>10)&0x3ffu)==100u && (pdo&0x3ffu)==90u &&
           (control&3u)==0u && ((control>>26)&7u)==0u &&
           (global[0]&1u) && (global[1]&7u)==1u && (global[2]&7u)==2u;
}

bool tps25751_read_port_state(uint8_t address,tps25751_port_state_t *state)
{
    uint8_t status[5],power[5],pd[4],cfg[18],length,profile[17],profile2[17];
    uint8_t status2[5],power2[5],pd2[4],cfg2[18],length2;
    if (!state) return false;
    memset(state,0,sizeof(*state));
    if (!framed_read(address,0x1a,status,5) || !framed_read(address,0x26,power,5) ||
        !framed_read(address,0x40,pd,4) || !read_port_configuration(address,cfg,&length) ||
        !read_source_profile(address,profile) ||
        !framed_read(address,0x1a,status2,5) || !framed_read(address,0x26,power2,5) ||
        !framed_read(address,0x40,pd2,4) || !read_port_configuration(address,cfg2,&length2) ||
        !read_source_profile(address,profile2) || memcmp(profile,profile2,sizeof(profile)) ||
        memcmp(status,status2,5) || memcmp(power,power2,5) || memcmp(pd,pd2,4) ||
        length!=length2 || memcmp(cfg,cfg2,length)) return false;
    uint32_t st=le32(status),pwr=le32(power),pdst=le32(pd);
    uint8_t pp1=(uint8_t)((pwr>>6)&7u),pp3=(uint8_t)((pwr>>12)&7u);
    state->source_profile_valid=source_profile_valid(profile);
    state->typec_mode=cfg[0]&3u;
    state->connected=(st&1u) && ((st>>1)&7u)>=6u;
    state->source=(st&(1u<<5))!=0;
    state->dfp=(st&(1u<<6))!=0;
    state->vconn_switch=power[0]&3u;
    state->vconn_enabled=state->vconn_switch>=2u;
    state->pp5v_enabled=pp1==2u;
    state->pphv_input_enabled=pp3==3u;
    state->power_path_fault=pp1==1u || pp3==1u;
    if (pp1>2u || pp3>3u || pp3==2u ||
        (state->connected && state->source!=((pdst&(1u<<6))!=0)) ||
        (state->pp5v_enabled && (!state->source || !state->connected)) ||
        (state->pphv_input_enabled && state->source)) return false;
    state->valid=true;
    return true;
}
