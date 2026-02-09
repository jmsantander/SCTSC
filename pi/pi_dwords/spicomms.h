/* Command Words */
#define  SPI_WRAP_AROUND    0x0000   /* cmd */
#define  CW_RESET_FEE     0x0100   /* cmd */
#define  CW_FEEs_PRESENT    0x0200   /* cmd */
#define  CW_FEE_POWER_CTL   0x0400   /* cmd */
#define  CW_RD_FEE0_I     0x0500   /* cmd */
#define  CW_RD_FEE8_I     0x0507   /* cmd */
#define  CW_RD_FEE16_I      0x050F   /* cmd */
#define  CW_RD_FEE24_I      0x0510   /* cmd */
#define  CW_RD_FEE0_V     0x0600   /* cmd */
#define  CW_RD_FEE8_V     0x0607   /* cmd */
#define  CW_RD_FEE16_V      0x060F   /* cmd */
#define  CW_RD_FEE24_V      0x0610   /* cmd */
#define  CW_RD_ENV          0x0700   /* cmd */
#define  CW_RD_HKPWB      0x0800   /* cmd */
#define  CW_PERI_TRIG       0x0900   /* cmd */
#define  CW_TRG_ADCS      0x0A00   /* cmd */
#define  CW_RESET_SI5338      0x0B0B   /* cmd */
#define  CW_RESET_I2C     0x0B0C   /* cmd */
#define  CW_RD_PWRSTATUS    0x0B00   /* cmd */
#define  CW_DACQ1_PWR_RESET  0x0C00   /* cmd */
#define  CW_DACQ2_PWR_RESET  0x0D00   /* cmd */
#define  SPI_SOM_HKFPGA   0xeb90 // Start of Message HKFPGA
#define  SPI_EOM_HKFPGA   0xeb09 // End of Message HKFPGA

#define  SPI_SOM_TFPGA    0xeb91 // Start of Message TFPGA
#define  SPI_EOM_TFPGA    0xeb0a // End of Message TFPGA
#define  SPI_WRAP_AROUND_TFPGA  0x0000   /* cmd */

#define  SPI_SET_nsTimer_TFPGA    0x0100   /* cmd */
#define  SPI_READ_nsTimer_TFPGA     0x0200   /* cmd */
#define  SPI_TRIGGERMASK_TFPGA  0x0300 /* cmd */
#define  SPI_TRIGGERMASK1_TFPGA 0x0400 /* cmd */
#define  SPI_TRIGGERMASK2_TFPGA 0x0500 /* cmd */
#define  SPI_TRIGGERMASK3_TFPGA 0x0600 /* cmd */
#define  SPI_READ_TRIGGER_NSTIMER_TFPGA 0x0700   /* cmd */
#define  SPI_HOLDOFF_TFPGA    0x0800   /* cmd */
#define  SPI_TRIGGER_TFPGA    0x0900   /* cmd */
#define  SPI_L1_TRIGGER_EN 0x0a00  /* cmd */
#define  RESET_TRIGGER_COUNT_AND_NSTIMER 0x0b00 /* cmd */
#define  SPI_READ_HIT_PATTERN     0x0c00   /* cmd */
#define  SPI_READ_HIT_PATTERN1    0x0d00   /* cmd */
#define  SPI_READ_HIT_PATTERN2    0x0e00   /* cmd */
#define  SPI_READ_HIT_PATTERN3    0x0f00   /* cmd */
#define  SPI_SET_ARRAY_SERDES_CONFIG 0x1000  /* cmd */
#define  SPI_SET_TACK_TYPE_MODE 0x1100 /* cmd */
#define  SPI_SET_TRIG_AT_TIME 0x1200 /* cmd */
#define  SPI_READ_DIAT_WORDS 0x1300 /* cmd */

#define  DWnull     0x0000   /* zero word */
