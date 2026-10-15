"""Parts and design limits for the separate AUX input path."""

FUSE_MPN = "0678H5000-02"
FUSE_MANUFACTURER = "Bel Fuse"
FUSE_FOOTPRINT = "ducktop2:Bel_0678H_3912"
FUSE_DATASHEET = "https://www.belfuse.com/media/datasheets/products/circuit-protection/ds-cp-0678h-series.pdf"
FUSE_DATASHEET_SHA256 = "7b3666fbc55208eb7b1d143cf79f1e4e43f6c2d9efb959dcc185f8e5b09ca4aa"
FUSE_RATED_A = 5.0
FUSE_RATED_DC_V = 125.0
FUSE_BREAKING_DC_A = 2000.0
FUSE_BODY_MAX_HEIGHT_MM = 3.18
FUSE_INSTALLED_HEIGHT_BUDGET_MM = 3.48
FUSE_TYPICAL_COLD_OHM = .016
FUSE_TYPICAL_MELTING_I2T = 10.0

# These are design allocations, not measured operating permissions.
AUX_MAX_SOURCE_BUDGET_MA = 3000
AUX_INITIAL_SOURCE_BUDGET_MA = 500
AUX_MIN_OPERATING_V = 7.0
AUX_MAX_OPERATING_V = 22.0
FUSE_CONTINUOUS_DESIGN_FACTOR = .75
FUSE_TEMPERATURE_FACTOR = .95
FUSE_LOCAL_AMBIENT_LIMIT_C = 85.0


def fuse_properties():
    return {
        "Manufacturer": FUSE_MANUFACTURER,
        "MPN": FUSE_MPN,
    }
