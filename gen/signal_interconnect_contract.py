"""Signal cables, shell returns and separate main-board ground straps."""
from generate_signal_interconnect import footprint_name

LEFT_PAIRS = (
    ('USBC1_SSRX_P', 'USBC1_SSRX_N'), ('USBC1_SSTX_P', 'USBC1_SSTX_N'),
    ('USBC2_SSRX_P', 'USBC2_SSRX_N'), ('USBC2_SSTX_P', 'USBC2_SSTX_N'),
    ('USBC1_DP', 'USBC1_DN'), ('USBC2_DP', 'USBC2_DN'),
    ('HUB_DS1_DP', 'HUB_DS1_DN'), ('HUB_DS4_DP', 'HUB_DS4_DN'),
)
LEFT_CONTROLS = (
    'PD1_I2C_SCL', 'PD1_I2C_SDA', 'PD1_TCPC_IRQ_N',
    'PD1_PATH_EN', 'PD1_VALID_N', 'PD1_EFUSE_FAULT_N',
    'PD_PROTECT_FAULT_N', 'SERVICE_MUX_RESET_N', 'PD2_SOURCE_PG',
    'USB_J11_PERMIT', 'USB_J12_PERMIT', 'HUB_PRT_CTL4', 'INTERNAL_USB_VBUS_VALID',
)
RIGHT_PAIRS = (
    ('TCP0_TX0_P', 'TCP0_TX0_N'), ('TCP0_TX1_P', 'TCP0_TX1_N'),
    ('TCP0_TXRX0_P', 'TCP0_TXRX0_N'), ('TCP0_TXRX1_P', 'TCP0_TXRX1_N'),
    ('GBE_HOST_RX_P', 'GBE_HOST_RX_N'), ('GBE_HOST_TX_P', 'GBE_HOST_TX_N'),
    ('GBE_REFCLK_P', 'GBE_REFCLK_N'),
    ('HUB_DS1_DP', 'HUB_DS1_DN'), ('HUB_DS4_DP', 'HUB_DS4_DN'),
)
RIGHT_CONTROLS = (
    'TCP0_DDC_SCL', 'TCP0_DDC_SDA', 'TCP0_HPD',
    'PD2_I2C_SCL', 'PD2_I2C_SDA', 'PD2_TCPC_IRQ_N',
    'PD2_PATH_EN', 'PD2_EFUSE_FAULT_N', 'PD_PROTECT_FAULT_N',
    'PD2_SOURCE_PG', 'USB_J11_PERMIT', 'USB_J12_PERMIT',
    'HUB_PRT_CTL4', 'MU_HOST_ACTIVE', 'PLTRST_SRC_N', 'PCIE_WAKE_N', 'GBE_CLKREQ_N',
)


def make_map(count, pairs, controls, control_grounds):
    values = ['GND']
    for pair in pairs:
        values.extend((*pair, 'GND'))
    result = dict(enumerate(values, 1))
    controls = iter(controls)
    for pin in range(len(values) + 1, count + 1):
        result[pin] = 'GND' if pin in control_grounds else next(controls)
    if next(controls, None) is not None:
        raise ValueError('control signals do not fit the cable')
    return result


LEFT_PINMAP = make_map(41, LEFT_PAIRS, LEFT_CONTROLS, {29, 33, 37})
RIGHT_PINMAP = make_map(51, RIGHT_PAIRS, RIGHT_CONTROLS, {32, 36, 40, 44, 48, 51})
INTERFACES = {
    'FPC101': {'count': 41, 'cable': '150230241', 'resistors': ('R2440', 'R2441'), 'straps': ('J2440', 'J2442')},
    'FPC102': {'count': 41, 'cable': '150230241', 'resistors': ('R2442', 'R2443'), 'straps': ('J2441', 'J2443')},
    'FPC103': {'count': 51, 'cable': '150230251', 'resistors': ('R2444', 'R2445'), 'straps': ('J2444', 'J2446')},
    'FPC104': {'count': 51, 'cable': '150230251', 'resistors': ('R2446', 'R2447'), 'straps': ('J2445', 'J2447')},
}
STRAP_PAIRS = (('J2440', 'J2441'), ('J2442', 'J2443'), ('J2444', 'J2445'), ('J2446', 'J2447'))
CABLE_LENGTH_MM = 51
CABLE_LENGTH_TOLERANCE_MM = 2
CABLE_IMPEDANCE_OHM = 100
CABLE_IMPEDANCE_TOLERANCE_OHM = 10
CABLE_CURRENT_ALL_LOADED_AT_23C_A = .4
CABLE_MAX_CONDUCTOR_TEMPERATURE_C = 80
ASSEMBLY_AMBIENT_MAX_C = 55
# These are receiving and completed-assembly requirements, not measured facts.
CABLE_CONDUCTOR_MIN_AT_20C_OHM = .040
STRAP_MPN = '1230'
STRAP_CUT_LENGTH_MM = 20
STRAP_COMPLETED_MAX_OHM = .001
SEAM_RETURN_DESIGN_MAX_A = 8
SEAM_GROUND_MAX_V = .008
SHELL_RESISTOR_MPN = 'ERJ3RQFR33V'
SHELL_RESISTOR_OHM = .33


def symbol_for(ref):
    return f"Conn_01x{INTERFACES[ref]['count']}_Signal_SH"


def footprint_for(ref):
    return 'ducktop2:' + footprint_name(INTERFACES[ref]['count'])


def mpn_for(ref):
    return f"503908{INTERFACES[ref]['count']}20"


def add_returns(s, ref):
    spec = INTERFACES[ref]
    shell = ref + '_SHELL'
    for index, resistor in enumerate(spec['resistors']):
        pins = s.place(resistor, 'R', '0.33', 110 + index * 30, 470,
            footprint='Resistor_SMD:R_0603_1608Metric',
            pin_nets={'1': (shell, 'local')},
            extra_props={'Manufacturer': 'Panasonic', 'MPN': SHELL_RESISTOR_MPN,
                'Datasheet': 'https://industrial.panasonic.com/ww/products/pt/current-sensing-chip-resistors/models/ERJ3RQFR33V',
                'Placement': 'one at each end of the connector shell; short connections to the adjacent ground plane'})
        s.gnd(*pins['2'])
    for index, pad_ref in enumerate(spec['straps']):
        pins = s.place(pad_ref, 'TestPoint', 'main ground strap', 310 + index * 35, 130,
            footprint='Connector_Wire:SolderWirePad_1x01_SMD_5x10mm', in_bom=False,
            extra_props={'AssemblyWire': 'Alpha Wire 1230 tinned copper braid; 20 mm cut length',
                'AssemblyResistance': 'each complete strap <=1 mOhm, including pads, vias and joints',
                'Assembly': 'two independently attached straps per seam; insulate and strain-relieve both',
                'Datasheet': 'https://www.alphawire.com/disteAPI/SpecPDF/DownloadProductSpecPdf?productPartNumber=1230'})
        s.gnd(*pins['1'])
    s.text(85, 505, 'Both ground straps must be fitted before the signal cable. Keep raw and protected battery returns separate from these main-board grounds.')
    s.text(85, 515, 'The shell uses two parallel 0.33 ohm returns at each connector. Numbered ground conductors connect directly to the local ground plane.')
