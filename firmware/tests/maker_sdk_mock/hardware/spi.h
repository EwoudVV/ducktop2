#include "pico/stdlib.h"
typedef struct {volatile uint32_t dr;} spi_hw_t;
typedef struct {spi_hw_t hw;} spi_inst_t;
extern spi_inst_t mock_spi;
#define spi0 (&mock_spi)
#define SPI_CPOL_0 0u
#define SPI_CPOL_1 1u
#define SPI_CPHA_0 0u
#define SPI_CPHA_1 1u
#define SPI_MSB_FIRST 0u
uint32_t spi_init(spi_inst_t *spi,uint32_t rate);
void spi_deinit(spi_inst_t *spi);
void spi_set_format(spi_inst_t *spi,unsigned bits,unsigned polarity,unsigned phase,unsigned order);
bool spi_is_writable(spi_inst_t *spi);
bool spi_is_readable(spi_inst_t *spi);
bool spi_is_busy(spi_inst_t *spi);
spi_hw_t *spi_get_hw(spi_inst_t *spi);
