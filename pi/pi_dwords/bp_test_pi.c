/*
 ============================================================================
 Name        : BP_TEST
 Author      : Phil Moore Richard Bose
 Version     : 5-12-2016
 Copyright   : Your copyright notice
 Description : CTA HKFPGA & TFPGA Debug test software using Raspberry Pi, Ansi-style
 ============================================================================
 */
#include <stdio.h>
#include <sys/io.h>  // routines for accessing I/O ports
#include <unistd.h>  // includes ioperm
#include <math.h>
#include <errno.h>
#include <string.h>
#include <stdlib.h>
#include <signal.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/select.h>
#include <time.h>
// #include <sys/ioctl.h>
#include <bcm2835.h> // Driver for SPI chip

#include "spicomms.h"

/* Functions */
void us_sleep(int us);
void ms_sleep(int ms);
void s_sleep(int s);
void tdelay(int msec);
void usdelay(int usec);
int kbhit(void);
void display_slavespi_data(unsigned short *data);
void print_slavespi_data(FILE *fptr, unsigned short *data);
void display_voltages (void);
void display_currents (void);
void display_fees_present (void);
void display_pwrbd_hskp(void);
void display_env_hskp(void);
void display_nstime_trigger_count(unsigned short *data);
void trig_adcs (void);
unsigned short spi_tword(unsigned short write_word) ;
void transfer_message(unsigned short *message, unsigned short *data) ;

/*  Global variables */
	

int main(void){
    unsigned short spi_message[11], data[11], i, i1, i2, i3;
    unsigned short j[32];
    unsigned short quit;
	unsigned long k;
    char key;
	unsigned short hit_pattern[32];

	if (!bcm2835_init())
	  return 1;
	bcm2835_spi_begin();
	bcm2835_spi_setBitOrder(BCM2835_SPI_BIT_ORDER_MSBFIRST); // The default
	// Set Mode to zero
	bcm2835_spi_setDataMode(BCM2835_SPI_MODE0);  
	// Set clock divider (BCM2835_SPI_CLOCK_DIVIDER_256) to give 1024 ns clock
	// nominal value needed by BP is 640 ns - slower works too
	// Tried 512 ns (BCM2835_SPI_CLOCK_DIVIDER_128) 8-10-2015 Seems OK
	bcm2835_spi_setClockDivider(BCM2835_SPI_CLOCK_DIVIDER_128); 
	bcm2835_spi_chipSelect(BCM2835_SPI_CS0);              
	bcm2835_spi_setChipSelectPolarity(BCM2835_SPI_CS0, LOW);  // the default

// load SPI wrap around message as default
	spi_message[0] = SPI_SOM_HKFPGA; //som
	spi_message[1] = SPI_WRAP_AROUND; //cw
	spi_message[2] = 0x0111;
	spi_message[3] = 0x1222;
	spi_message[4] = 0x2333;
	spi_message[5] = 0x3444;
	spi_message[6] = 0x4555;
	spi_message[7] = 0x5666;
	spi_message[8] = 0x6777;
	spi_message[9] = 0x7888;
	spi_message[10] = SPI_EOM_HKFPGA; //not used
    printf("\n\n************* CTA HKFPGA Readout Test Program 10-14-2020 ***************\n");

    key = '+';
    quit = 0;
    while (quit == 0) {
		if (key != '\n') {
			system("date");
			printf("Press 'm' to display menu x to exit \n");
		}
		key = getchar();
		
		switch (key){
/****************************************************************************************************/
        case 'm': // display menu
            printf("----------------------- Command Menu ---------------------------------\n");
			printf("w. HKFPGA wrap around                 p. Display FEEs Present\n");
			printf("v. Display FEE 12V                    i. Display FEE I      \n");
			printf("h. Power BOard HSKP                   e. ENV HSKP\n");
            printf("r. Reset FEE                          n. Power on/off FEE     \n");
			printf("t. Send Cal Trigger                   u. Power Board Status   \n");
			printf("1. Reset DACQ1 Power                  2. Reset DACQ2 Power \n");
			printf("                       \n");
			printf("a. TFPGA wrap around                  k. TFPGA Trigger\n");
			printf("b. TFPGA set nsTimer                  c. TFPGA Read nsTimer, Counts, Rates\n");
			printf("f. TFPGA Trigger Time Read            g. TFPGA En/Disable Trigger/TACK\n");
			printf("j. Set Trigger Mask                   l. Reset Trigger Counter and nsTimer\n");
			printf("5. Set Trigger Mask for single group   \n");
			printf("q. Read Hit Pattern                   y. Set Array Board COnfig\n");
			printf("z. Set Tack Type and Mode             d. Set Trigger at Time\n");
			printf("s. Send a SYNC MEssage                o. Set Hold Off  \n");
			printf("3. Read DIAT Words                    4. Reset Si5338 clock distributor \n");
			printf("6. Reset I2C bus                      9. Write trigger patterns to ASCII file \n");
			printf("$. Write trigger patterns to binary file (dataword) \n");
			printf("*. Write trigger patterns to binary file (dataword) \n");
			printf("----------------------- Misc Commands ------------------------------\n");
            printf("m. Menu                               x. exit \n");
			printf("--------------------------------------------------------------------\n");
            break;

		case 'a': // TFPGA wrap around
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_WRAP_AROUND_TFPGA; //cw
			spi_message[2] = 0xC0FE;
			spi_message[3] = 0xBEEF;
			spi_message[4] = 0xF1EA;
			spi_message[5] = 0xD0CC;
			spi_message[6] = 0x6555;
			spi_message[7] = 0x7666;
			spi_message[8] = 0x8777;
			spi_message[9] = 0xa888;
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
            break;	
			
		case 'b': // Set 64 bit nanosecond time 
			printf ("Enter nsTimer value 63-48 bits in hex : ");
			scanf ("%hx",&i);
			printf ("Enter nsTimer value 47-32 bits in hex : ");
			scanf ("%hx",&i1);
			printf ("Enter nsTimer value 31-16 bits in hex : ");
			scanf ("%hx",&i2);
			printf ("Enter nsTimer value 15-0  bits in hex : ");
			scanf ("%hx",&i3);
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_SET_nsTimer_TFPGA; //cw
			spi_message[2] = i;
			spi_message[3] = i1;
			spi_message[4] = i2;
			spi_message[5] = i3;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
            break;
			
		case 'c': // Read 64-bit nanosecond time
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_nsTimer_TFPGA; //cw
			spi_message[2] = 0X0001;
			spi_message[3] = 0X0002;
			spi_message[4] = 0X0003;
			spi_message[5] = 0X0004;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			display_nstime_trigger_count(data);
            break;

		case 'd': // Set Trig at time 
			printf ("Enter Trig at Time value 63-48 bits in hex: ");
			scanf ("%hx",&i);
			printf ("Enter Trig at Time value 47-32 bits in hex: ");
			scanf ("%hx",&i1);
			printf ("Enter Trig at Time value 31-16 bits in hex: ");
			scanf ("%hx",&i2);
			printf ("Enter Trig at Time value 15-0  bits in hex: ");
			scanf ("%hx",&i3);
			
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_SET_TRIG_AT_TIME; //cw
			spi_message[2] = i;
			spi_message[3] = i1;
			spi_message[4] = i2;
			spi_message[5] = i3;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data); 
			
            break;
			
		case 'e': // ENV Housekeeping Includes DACQ Current, FEE33 current and voltage, ENV1-4
			trig_adcs();
			display_env_hskp();
			break;
			
		case 'f': // Read time of last trigger
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_TRIGGER_NSTIMER_TFPGA; //cw
			spi_message[2] = 0x0000;
			spi_message[3] = 0x0000;
			spi_message[4] = 0x0000;
			spi_message[5] = 0x0000;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
		break;

		case 'g': // Enable and Disable Hardware Trigger
			printf("Enter En/Disable Triggers and TACKs in Hex:\n");
			printf("Bit 0 is Phase A logic, 1 Phase B, 2 Phase C, 3 Phase D\n");
			printf("Bit 4 is External Trigger\n");
			printf("Bit 5 is TACK messages to TMs 0-15, 6 TMs 16-31\n ");
			scanf("%hx",&i);
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_L1_TRIGGER_EN; //cw
			spi_message[2] = i;
			spi_message[3] = 0x0002;
			spi_message[4] = 0x0003;
			spi_message[5] = 0x0004;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
		break;
			
		case 'h': // Power BOard Housekeeping
			trig_adcs();
			display_pwrbd_hskp();
			break;
			
		case 'i': // FEEs Housekeeping currents
			trig_adcs();
			display_currents();
			break;
		
		case '5': // Set Trigger Mask from input, for single group
			printf("Setting Trigger Mask from input\n");
			int module;
			int asic;
			int group;
			printf("specify module for triggering!\n");
			scanf("%d",&module);
			printf("specify asic for triggering!\n");
			scanf("%d",&asic);
			printf("specify group for triggering!\n");
			scanf("%d",&group);
			for(i=0;i<32;i++)
			{
				if(i==module){
				//	j[i] = 0xffff & ~( 0xf << asic*4);
					if(asic%2==0){
						if(group<2){
							j[i] = 0xffff & ~( (0xf & (0x1 << group) ) << asic*4);
						}
						else{
							j[i] = 0xffff & ~( (0xf & (0x1 << ((group-2) ) ) ) << (asic+1)*4);
						}
					}
					else{
						if(group>1){
							j[i] = 0xffff & ~( (0xf & (0x1 << group) ) << asic*4);
						}
						else{
							j[i] = 0xffff & ~( (0xf & (0x1 << ((group)+2 ) ) ) << (asic-1)*4);
						}
					}

			//		printf("0x%04x\n", j[i]);
				}
				else{
					j[i] = 0xffff;
			//		printf("0x%04x\n", j[i]);
				}
			//	printf("\n");
			}
			
			
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK_TFPGA; //cw
			spi_message[2] = j[0];
			spi_message[3] = j[1];
			spi_message[4] = j[2];
			spi_message[5] = j[3];
			spi_message[6] = j[4];
			spi_message[7] = j[5];
			spi_message[8] = j[6];
			spi_message[9] = j[7];			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			//printf("      %04x %04x %04x %04x\n", data[2],data[3],data[4],data[5]);
			printf(" %04x %04x %04x %04x", data[6],data[7],data[8],data[9]);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK1_TFPGA; //cw
			spi_message[2] = j[8];
			spi_message[3] = j[9];
			spi_message[4] = j[10];
			spi_message[5] = j[11];
			spi_message[6] = j[12];
			spi_message[7] = j[13];
			spi_message[8] = j[14];
			spi_message[9] = j[15];			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			printf(" %04x %04x\n", data[2],data[3]);
			printf(" %04x %04x %04x %04x %04x %04x\n",data[4],data[5],data[6],data[7],data[8],data[9]);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK2_TFPGA; //cw
			spi_message[2] = j[16];
			spi_message[3] = j[17];
			spi_message[4] = j[18];
			spi_message[5] = j[19];
			spi_message[6] = j[20];
			spi_message[7] = j[21];
			spi_message[8] = j[22];
			spi_message[9] = j[23];			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			printf(" %04x %04x %04x %04x %04x %04x\n",data[2],data[3],data[4],data[5],data[6],data[7]);
			printf(" %04x %04x", data[8],data[9]);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK3_TFPGA; //cw
			spi_message[2] = j[24];
			spi_message[3] = j[25];
			spi_message[4] = j[26];
			spi_message[5] = j[27];
			spi_message[6] = j[28];
			spi_message[7] = j[29];
			spi_message[8] = j[30];
			spi_message[9] = j[31];			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			printf(" %04x %04x %04x %04x\n",data[2],data[3],data[4],data[5]);
			printf("      %04x %04x %04x %04x\n",data[6],data[7],data[8],data[9]);
            break;
		
		case 'j': // Set Trigger Mask from file
			printf("Setting Trigger Mask from file trigger_mask\n");
			FILE *myfile;
			printf("specify fiilename to read!\n");
			char filename[50];
			scanf("%s",&filename[0]);
			myfile = fopen(filename,"r");
			for(i=0;i<32;i++)
			{
			fscanf(myfile, "%hx", &j[i]);;
			//printf("%d ", i);
			}
			printf("\n");
			
			//for(i=0;i<32;i++)
			//{
			//	printf("J%d. ",i);
			//	printf("0x%04x\n", j[i]);
			//}
			 

			fclose(myfile);
			
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK_TFPGA; //cw
			spi_message[2] = j[0];
			spi_message[3] = j[1];
			spi_message[4] = j[2];
			spi_message[5] = j[3];
			spi_message[6] = j[4];
			spi_message[7] = j[5];
			spi_message[8] = j[6];
			spi_message[9] = j[7];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			//printf("      %04x %04x %04x %04x\n", data[2],data[3],data[4],data[5]);
			printf(" %04x", data[9]);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK1_TFPGA; //cw
			spi_message[2] = j[8];
			spi_message[3] = j[9];
			spi_message[4] = j[10];
			spi_message[5] = j[11];
			spi_message[6] = j[12];
			spi_message[7] = j[13];
			spi_message[8] = j[14];
			spi_message[9] = j[15];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			//printf(" %04x\n", data[2]);
			printf(" %04x %04x %04x %04x\n", data[2],data[3],data[4],data[5]);
			printf(" %04x %04x %04x %04x", data[6],data[7],data[8],data[9]);
			
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK2_TFPGA; //cw
			spi_message[2] = j[16];
			spi_message[3] = j[17];
			spi_message[4] = j[18];
			spi_message[5] = j[19];
			spi_message[6] = j[20];
			spi_message[7] = j[21];
			spi_message[8] = j[22];
			spi_message[9] = j[23];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			printf(" %04x\n", data[2]);
			printf(" %04x %04x %04x %04x %04x\n",data[3],data[4],data[5],data[6],data[7]);
			printf(" %04x %04x", data[8], data[9]);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK3_TFPGA; //cw
			spi_message[2] = j[24];
			spi_message[3] = j[25];
			spi_message[4] = j[26];
			spi_message[5] = j[27];
			spi_message[6] = j[28];
			spi_message[7] = j[29];
			spi_message[8] = j[30];
			spi_message[9] = j[31];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			printf(" %04x %04x %04x\n",data[2],data[3],data[4]);
			printf(" %04x %04x %04x %04x %04x\n", data[5],data[6],data[7],data[8],data[9]);
		break;

		case '8': // Set Trigger Mask from file
			printf("Setting Trigger Mask directly\n");


			char moduleTrig[32];
			printf("Input module-trigger mask:");
			scanf("%32c",&moduleTrig[0]);

			for(i=0;i<32;i++)
			{
			if(moduleTrig[i]=='1'){
				j[i]=0x0000;
				}
			else{
				j[i]=0xffff;
				}

			//printf("%d ", i);
			}
			printf("\n");
			
			//for(i=0;i<32;i++)
			//{
			//	printf("J%d. ",i);
			//	printf("0x%04x\n", j[i]);
			//}
			 

			fclose(myfile);
			
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK_TFPGA; //cw
			spi_message[2] = j[0];
			spi_message[3] = j[1];
			spi_message[4] = j[2];
			spi_message[5] = j[3];
			spi_message[6] = j[4];
			spi_message[7] = j[5];
			spi_message[8] = j[6];
			spi_message[9] = j[7];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			//printf("      %04x %04x %04x %04x\n", data[2],data[3],data[4],data[5]);
			printf(" %04x", data[9]);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK1_TFPGA; //cw
			spi_message[2] = j[8];
			spi_message[3] = j[9];
			spi_message[4] = j[10];
			spi_message[5] = j[11];
			spi_message[6] = j[12];
			spi_message[7] = j[13];
			spi_message[8] = j[14];
			spi_message[9] = j[15];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			//printf(" %04x\n", data[2]);
			printf(" %04x %04x %04x %04x\n", data[2],data[3],data[4],data[5]);
			printf(" %04x %04x %04x %04x", data[6],data[7],data[8],data[9]);
			
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK2_TFPGA; //cw
			spi_message[2] = j[16];
			spi_message[3] = j[17];
			spi_message[4] = j[18];
			spi_message[5] = j[19];
			spi_message[6] = j[20];
			spi_message[7] = j[21];
			spi_message[8] = j[22];
			spi_message[9] = j[23];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			printf(" %04x\n", data[2]);
			printf(" %04x %04x %04x %04x %04x\n",data[3],data[4],data[5],data[6],data[7]);
			printf(" %04x %04x", data[8], data[9]);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_TRIGGERMASK3_TFPGA; //cw
			spi_message[2] = j[24];
			spi_message[3] = j[25];
			spi_message[4] = j[26];
			spi_message[5] = j[27];
			spi_message[6] = j[28];
			spi_message[7] = j[29];
			spi_message[8] = j[30];
			spi_message[9] = j[31];
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			printf(" %04x %04x %04x\n",data[2],data[3],data[4]);
			printf(" %04x %04x %04x %04x %04x\n", data[5],data[6],data[7],data[8],data[9]);
		break;

		case 'k': // TFPGA software trigger
			
			//int cal_runDuration;
			//int cal_freq;
			//printf("Specify run duration in seconds!\n");
			//scanf("%d",&cal_runDuration);
			//printf("Specify trigger frequency in Hz!\n");
			//scanf("%d",&cal_freq);
			//int cal_msPeriod = 1000/cal_freq;
			//int cal_usPeriod = 1000000/cal_freq;
			//ms_sleep(1000);

			//for(i=0;i<10000;i++){
                        spi_message[0] = SPI_SOM_TFPGA; //som
                        spi_message[1] = SPI_TRIGGER_TFPGA; //cw
                        spi_message[2] = 0x3111;
                        spi_message[3] = 0x3222;
                        spi_message[4] = 0x2333;
                        spi_message[5] = 0x3444;
                        spi_message[6] = 0x4555;
                        spi_message[7] = 0x5666;
                        spi_message[8] = 0x6777;
                        spi_message[9] = 0xa888;
                        spi_message[10] = SPI_EOM_TFPGA; //not used
                        transfer_message(spi_message,data);
			//us_sleep(cal_usPeriod);
			//ms_sleep(10);
			//}

			display_slavespi_data(data);
            break;	
			  
			
		case 'l': // Reset nanosceond time and trigger count
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = RESET_TRIGGER_COUNT_AND_NSTIMER; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			break;

		case 'n': // Power Control FEE
            printf ("Enter FEEs to Power ON/OFF (32 bits 0=off 1=on) 0-0xFFFFFFFF: ");
            scanf ("%lx", &k); 
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_FEE_POWER_CTL; //cw
			spi_message[2] = k >> 16;
            spi_message[3] = k & 0x0000ffff;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
            break;  
			
		case 'o': // Set Hold Off time before next trigger ~i * 4 ns
			printf ("Enter Hold Off in hex : ");
			scanf ("%hx",&i);
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_HOLDOFF_TFPGA; //cw
			spi_message[2] = i;
			spi_message[3] = 0x0002;
			spi_message[4] = 0x0003;
			spi_message[5] = 0x0004;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
            break;	
			
		case 'p': // FEEs present
			display_fees_present ();
            break;
		
    case '*': // Return Hit Pattern

      printf("Enter the frequency of the hit pattern recording [Hz]: ");
      float freq;
      scanf("%f", &freq);

      printf("Enter the duration of the hit pattern recordingt [s]: ");
      float dt;
      scanf("%f", &dt);

      char sdt[32];
      sprintf(sdt, "%f", dt);

      char sfreq[32];
      sprintf(sfreq, "%f", freq);

      int N = (int)(freq * dt);
      float period = 1. / freq;
      
      printf("%s %0.1f %s %0.1f %s", "Hit patterns will be read for", dt, "s at a frequency of", freq, "Hz\n");
      printf("%s %d %s %0.3f %s", "Will read", N, "patterns with a period of", period, "s\n");
      printf("\n");

      FILE *fptr;
      fptr = fopen("hitpattern_dwords.txt", "w");
      fprintf(fptr, "N: %d, freq: %f\n", N, freq);

      for (int step = 0; step < N; step++) {
      printf("Step: %d\n", step+1);
      fprintf(fptr, "Step: %d\n", step+1);
      //fprintf(fptr, "Date: %d-%02d-%02d %02d:%02d:%02d\n", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);
      
      struct timespec ts;
      timespec_get(&ts, TIME_UTC);
      char buff[100];
      strftime(buff, sizeof buff, "%D %T", gmtime(&ts.tv_sec));
      fprintf(fptr, "Current time: %s.%09ld UTC\n", buff, ts.tv_nsec);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_HIT_PATTERN; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			print_slavespi_data(fptr, data);

			spi_message[1] = SPI_READ_HIT_PATTERN1; //cw
			transfer_message(spi_message,data);
			print_slavespi_data(fptr, data);
			
			spi_message[1] = SPI_READ_HIT_PATTERN2; //cw
			transfer_message(spi_message,data);
			print_slavespi_data(fptr, data);
			
			spi_message[1] = SPI_READ_HIT_PATTERN3; //cw
			transfer_message(spi_message,data);
			print_slavespi_data(fptr, data);

      double period_int;
      double period_frac = modf(period, &period_int);

      if ((int) period_int > 0) {
        s_sleep((int) period_int);
      }

      float period_frac_ms = period_frac * 1000;

      if ((int) period_frac_ms > 0) {
        ms_sleep((int) period_frac_ms);
      }

      }

      fclose(fptr);
      printf("Closing hit pattern file\n\n");
			
		  break;

		case '7': // Return Hit Pattern
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_HIT_PATTERN; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[31-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN1; //cw
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[23-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN2; //cw
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[15-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN3; //cw
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[7-i] = data[i+2];
			}
			printf("Hit pattern read:\n");
			
			for(i=0;i<32;i++){
				printf("%4x, \n", hit_pattern[i]);
			}
		break;

		case 'q': // Display Hit Pattern
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_HIT_PATTERN; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[31-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN1; //cw
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[23-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN2; //cw
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[15-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN3; //cw
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[7-i] = data[i+2];
			}
			
			printf("\n");
			/*
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0008) >>3, //451
				(hit_pattern[28] & 0x0080) >>7, //455
				(hit_pattern[28] & 0x0800) >>11, //459
				(hit_pattern[28] & 0x8000) >>15, //463
				(hit_pattern[29] & 0x0008) >>3, //467
				(hit_pattern[29] & 0x0080) >>7, //471
				(hit_pattern[29] & 0x0800) >>11, //475
				(hit_pattern[29] & 0x8000) >>15, //479
				(hit_pattern[30] & 0x0008) >>3, //483
				(hit_pattern[30] & 0x0080) >>7, //487
				(hit_pattern[30] & 0x0800) >>11, //491
				(hit_pattern[30] & 0x8000) >>15, //495
				(hit_pattern[31] & 0x0008) >>3, //499
				(hit_pattern[31] & 0x0080) >>7, //503
				(hit_pattern[31] & 0x0800) >>11, //507
				(hit_pattern[31] & 0x8000) >>15 //511
				);
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0004) >>2, //450
				(hit_pattern[28] & 0x0040) >>6, //454
				(hit_pattern[28] & 0x0400) >>10, //458
				(hit_pattern[28] & 0x4000) >>14, //462
				(hit_pattern[29] & 0x0004) >>2, //466
				(hit_pattern[29] & 0x0040) >>6, //470
				(hit_pattern[29] & 0x0400) >>10, //474
				(hit_pattern[29] & 0x4000) >>14, //478
				(hit_pattern[30] & 0x0004) >>2, //482
				(hit_pattern[30] & 0x0040) >>6, //486
				(hit_pattern[30] & 0x0400) >>10, //490
				(hit_pattern[30] & 0x4000) >>14, //494
				(hit_pattern[31] & 0x0004) >>2, //498
				(hit_pattern[31] & 0x0040) >>6, //502
				(hit_pattern[31] & 0x0400) >>10, //506
				(hit_pattern[31] & 0x4000) >>14 //510
				);
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0002) >>1, //449
				(hit_pattern[28] & 0x0020) >>5, //453
				(hit_pattern[28] & 0x0200) >>9, //457
				(hit_pattern[28] & 0x2000) >>13, //461
				(hit_pattern[29] & 0x0002) >>1, //465
				(hit_pattern[29] & 0x0020) >>5, //469
				(hit_pattern[29] & 0x0200) >>9, //473
				(hit_pattern[29] & 0x2000) >>13, //477
				(hit_pattern[30] & 0x0002) >>1, //481
				(hit_pattern[30] & 0x0020) >>5, //485
				(hit_pattern[30] & 0x0200) >>9, //489
				(hit_pattern[30] & 0x2000) >>13, //493
				(hit_pattern[31] & 0x0002) >>1, //497
				(hit_pattern[31] & 0x0020) >>5, //501
				(hit_pattern[31] & 0x0200) >>9, //505
				(hit_pattern[31] & 0x2000) >>13 //509
				);
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0001) >>0, //448
				(hit_pattern[28] & 0x0010) >>4, //452
				(hit_pattern[28] & 0x0100) >>8, //456
				(hit_pattern[28] & 0x1000) >>12, //460
				(hit_pattern[29] & 0x0001) >>0, //464
				(hit_pattern[29] & 0x0010) >>4, //468
				(hit_pattern[29] & 0x0100) >>8, //472
				(hit_pattern[29] & 0x1000) >>12, //476
				(hit_pattern[30] & 0x0001) >>0, //480
				(hit_pattern[30] & 0x0010) >>4, //484
				(hit_pattern[30] & 0x0100) >>8, //488
				(hit_pattern[30] & 0x1000) >>12, //492
				(hit_pattern[31] & 0x0001) >>0, //496
				(hit_pattern[31] & 0x0010) >>4, //500
				(hit_pattern[31] & 0x0100) >>8, //504
				(hit_pattern[31] & 0x1000) >>12 //508
				);
				
			printf("\n");
			*/
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0008) >>3, //
				(hit_pattern[24] & 0x0080) >>7, //
				(hit_pattern[24] & 0x0800) >>11, //
				(hit_pattern[24] & 0x8000) >>15, //367
				(hit_pattern[23] & 0x0008) >>3, //
				(hit_pattern[23] & 0x0080) >>7, //
				(hit_pattern[23] & 0x0800) >>11, //
				(hit_pattern[23] & 0x8000) >>15, //
				(hit_pattern[22] & 0x0008) >>3, //
				(hit_pattern[22] & 0x0080) >>7, //
				(hit_pattern[22] & 0x0800) >>11, //
				(hit_pattern[22] & 0x8000) >>15, //
				(hit_pattern[21] & 0x0008) >>3, //
				(hit_pattern[21] & 0x0080) >>7, //
				(hit_pattern[21] & 0x0800) >>11, //
				(hit_pattern[21] & 0x8000) >>15, //
				(hit_pattern[20] & 0x0008) >>3, //
				(hit_pattern[20] & 0x0080) >>7, //
				(hit_pattern[20] & 0x0800) >>11, //
				(hit_pattern[20] & 0x8000) >>15 //
				);
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0004) >>2, //
				(hit_pattern[24] & 0x0040) >>6, //
				(hit_pattern[24] & 0x0400) >>10, //
				(hit_pattern[24] & 0x4000) >>14, //366
				(hit_pattern[23] & 0x0004) >>2, //
				(hit_pattern[23] & 0x0040) >>6, //
				(hit_pattern[23] & 0x0400) >>10, //
				(hit_pattern[23] & 0x4000) >>14, //
				(hit_pattern[22] & 0x0004) >>2, //
				(hit_pattern[22] & 0x0040) >>6, //
				(hit_pattern[22] & 0x0400) >>10, //
				(hit_pattern[22] & 0x4000) >>14, //
				(hit_pattern[21] & 0x0004) >>2, //
				(hit_pattern[21] & 0x0040) >>6, //
				(hit_pattern[21] & 0x0400) >>10, //
				(hit_pattern[21] & 0x4000) >>14, //
				(hit_pattern[20] & 0x0004) >>2, //
				(hit_pattern[20] & 0x0040) >>6, //
				(hit_pattern[20] & 0x0400) >>10, //
				(hit_pattern[20] & 0x4000) >>14 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0002) >>1, //
				(hit_pattern[24] & 0x0020) >>5, //
				(hit_pattern[24] & 0x0200) >>9, //
				(hit_pattern[24] & 0x2000) >>13, //365
				(hit_pattern[23] & 0x0002) >>1, //
				(hit_pattern[23] & 0x0020) >>5, //
				(hit_pattern[23] & 0x0200) >>9, //
				(hit_pattern[23] & 0x2000) >>13, //
				(hit_pattern[22] & 0x0002) >>1, //
				(hit_pattern[22] & 0x0020) >>5, //
				(hit_pattern[22] & 0x0200) >>9, //
				(hit_pattern[22] & 0x2000) >>13, //
				(hit_pattern[21] & 0x0002) >>1, //
				(hit_pattern[21] & 0x0020) >>5, //
				(hit_pattern[21] & 0x0200) >>9, //
				(hit_pattern[21] & 0x2000) >>13, //
				(hit_pattern[20] & 0x0002) >>1, //
				(hit_pattern[20] & 0x0020) >>5, //
				(hit_pattern[20] & 0x0200) >>9, //
				(hit_pattern[20] & 0x2000) >>13 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0001) >>0, //352
				(hit_pattern[24] & 0x0010) >>4, //356
				(hit_pattern[24] & 0x0100) >>8, //360
				(hit_pattern[24] & 0x1000) >>12, //365
				(hit_pattern[23] & 0x0001) >>0, //
				(hit_pattern[23] & 0x0010) >>4, //
				(hit_pattern[23] & 0x0100) >>8, //
				(hit_pattern[23] & 0x1000) >>12, //
				(hit_pattern[22] & 0x0001) >>0, //
				(hit_pattern[22] & 0x0010) >>4, //
				(hit_pattern[22] & 0x0100) >>8, //
				(hit_pattern[22] & 0x1000) >>12, //
				(hit_pattern[21] & 0x0001) >>0, //
				(hit_pattern[21] & 0x0010) >>4, //
				(hit_pattern[21] & 0x0100) >>8, //
				(hit_pattern[21] & 0x1000) >>12, //
				(hit_pattern[20] & 0x0001) >>0, //
				(hit_pattern[20] & 0x0010) >>4, //
				(hit_pattern[20] & 0x0100) >>8, //
				(hit_pattern[20] & 0x1000) >>12 //
				);
				
				printf("\n");
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0008) >>3, //
				(hit_pattern[19] & 0x0080) >>7, //
				(hit_pattern[19] & 0x0800) >>11, //
				(hit_pattern[19] & 0x8000) >>15, //
				(hit_pattern[18] & 0x0008) >>3, //
				(hit_pattern[18] & 0x0080) >>7, //
				(hit_pattern[18] & 0x0800) >>11, //
				(hit_pattern[18] & 0x8000) >>15, //
				(hit_pattern[17] & 0x0008) >>3, //
				(hit_pattern[17] & 0x0080) >>7, //
				(hit_pattern[17] & 0x0800) >>11, //
				(hit_pattern[17] & 0x8000) >>15, //
				(hit_pattern[16] & 0x0008) >>3, //
				(hit_pattern[16] & 0x0080) >>7, //
				(hit_pattern[16] & 0x0800) >>11, //
				(hit_pattern[16] & 0x8000) >>15, //
				(hit_pattern[15] & 0x0008) >>3, //
				(hit_pattern[15] & 0x0080) >>7, //
				(hit_pattern[15] & 0x0800) >>11, //
				(hit_pattern[15] & 0x8000) >>15 //
				);
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0004) >>2, //
				(hit_pattern[19] & 0x0040) >>6, //
				(hit_pattern[19] & 0x0400) >>10, //
				(hit_pattern[19] & 0x4000) >>14, //
				(hit_pattern[18] & 0x0004) >>2, //
				(hit_pattern[18] & 0x0040) >>6, //
				(hit_pattern[18] & 0x0400) >>10, //
				(hit_pattern[18] & 0x4000) >>14, //
				(hit_pattern[17] & 0x0004) >>2, //
				(hit_pattern[17] & 0x0040) >>6, //
				(hit_pattern[17] & 0x0400) >>10, //
				(hit_pattern[17] & 0x4000) >>14, //
				(hit_pattern[16] & 0x0004) >>2, //
				(hit_pattern[16] & 0x0040) >>6, //
				(hit_pattern[16] & 0x0400) >>10, //
				(hit_pattern[16] & 0x4000) >>14, //
				(hit_pattern[15] & 0x0004) >>2, //
				(hit_pattern[15] & 0x0040) >>6, //
				(hit_pattern[15] & 0x0400) >>10, //
				(hit_pattern[15] & 0x4000) >>14 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0002) >>1, //
				(hit_pattern[19] & 0x0020) >>5, //
				(hit_pattern[19] & 0x0200) >>9, //
				(hit_pattern[19] & 0x2000) >>13, //365
				(hit_pattern[18] & 0x0002) >>1, //
				(hit_pattern[18] & 0x0020) >>5, //
				(hit_pattern[18] & 0x0200) >>9, //
				(hit_pattern[18] & 0x2000) >>13, //
				(hit_pattern[17] & 0x0002) >>1, //
				(hit_pattern[17] & 0x0020) >>5, //
				(hit_pattern[17] & 0x0200) >>9, //
				(hit_pattern[17] & 0x2000) >>13, //
				(hit_pattern[16] & 0x0002) >>1, //
				(hit_pattern[16] & 0x0020) >>5, //
				(hit_pattern[16] & 0x0200) >>9, //
				(hit_pattern[16] & 0x2000) >>13, //
				(hit_pattern[15] & 0x0002) >>1, //
				(hit_pattern[15] & 0x0020) >>5, //
				(hit_pattern[15] & 0x0200) >>9, //
				(hit_pattern[15] & 0x2000) >>13 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0001) >>0, //
				(hit_pattern[19] & 0x0010) >>4, //
				(hit_pattern[19] & 0x0100) >>8, //
				(hit_pattern[19] & 0x1000) >>12, //
				(hit_pattern[18] & 0x0001) >>0, //
				(hit_pattern[18] & 0x0010) >>4, //
				(hit_pattern[18] & 0x0100) >>8, //
				(hit_pattern[18] & 0x1000) >>12, //
				(hit_pattern[17] & 0x0001) >>0, //
				(hit_pattern[17] & 0x0010) >>4, //
				(hit_pattern[17] & 0x0100) >>8, //
				(hit_pattern[17] & 0x1000) >>12, //
				(hit_pattern[16] & 0x0001) >>0, //
				(hit_pattern[16] & 0x0010) >>4, //
				(hit_pattern[16] & 0x0100) >>8, //
				(hit_pattern[16] & 0x1000) >>12, //
				(hit_pattern[15] & 0x0001) >>0, //
				(hit_pattern[15] & 0x0010) >>4, //
				(hit_pattern[15] & 0x0100) >>8, //
				(hit_pattern[15] & 0x1000) >>12 //
				);
				printf("\n");
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0008) >>3, //
				(hit_pattern[14] & 0x0080) >>7, //
				(hit_pattern[14] & 0x0800) >>11, //
				(hit_pattern[14] & 0x8000) >>15, //
				(hit_pattern[13] & 0x0008) >>3, //
				(hit_pattern[13] & 0x0080) >>7, //
				(hit_pattern[13] & 0x0800) >>11, //
				(hit_pattern[13] & 0x8000) >>15, //
				(hit_pattern[12] & 0x0008) >>3, //
				(hit_pattern[12] & 0x0080) >>7, //
				(hit_pattern[12] & 0x0800) >>11, //
				(hit_pattern[12] & 0x8000) >>15, //
				(hit_pattern[11] & 0x0008) >>3, //
				(hit_pattern[11] & 0x0080) >>7, //
				(hit_pattern[11] & 0x0800) >>11, //
				(hit_pattern[11] & 0x8000) >>15, //
				(hit_pattern[10] & 0x0008) >>3, //
				(hit_pattern[10] & 0x0080) >>7, //
				(hit_pattern[10] & 0x0800) >>11, //
				(hit_pattern[10] & 0x8000) >>15 //
				);
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0004) >>2, //
				(hit_pattern[14] & 0x0040) >>6, //
				(hit_pattern[14] & 0x0400) >>10, //
				(hit_pattern[14] & 0x4000) >>14, //
				(hit_pattern[13] & 0x0004) >>2, //
				(hit_pattern[13] & 0x0040) >>6, //
				(hit_pattern[13] & 0x0400) >>10, //
				(hit_pattern[13] & 0x4000) >>14, //
				(hit_pattern[12] & 0x0004) >>2, //
				(hit_pattern[12] & 0x0040) >>6, //
				(hit_pattern[12] & 0x0400) >>10, //
				(hit_pattern[12] & 0x4000) >>14, //
				(hit_pattern[11] & 0x0004) >>2, //
				(hit_pattern[11] & 0x0040) >>6, //
				(hit_pattern[11] & 0x0400) >>10, //
				(hit_pattern[11] & 0x4000) >>14, //
				(hit_pattern[10] & 0x0004) >>2, //
				(hit_pattern[10] & 0x0040) >>6, //
				(hit_pattern[10] & 0x0400) >>10, //
				(hit_pattern[10] & 0x4000) >>14 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0002) >>1, //
				(hit_pattern[14] & 0x0020) >>5, //
				(hit_pattern[14] & 0x0200) >>9, //
				(hit_pattern[14] & 0x2000) >>13, //365
				(hit_pattern[13] & 0x0002) >>1, //
				(hit_pattern[13] & 0x0020) >>5, //
				(hit_pattern[13] & 0x0200) >>9, //
				(hit_pattern[13] & 0x2000) >>13, //
				(hit_pattern[12] & 0x0002) >>1, //
				(hit_pattern[12] & 0x0020) >>5, //
				(hit_pattern[12] & 0x0200) >>9, //
				(hit_pattern[12] & 0x2000) >>13, //
				(hit_pattern[11] & 0x0002) >>1, //
				(hit_pattern[11] & 0x0020) >>5, //
				(hit_pattern[11] & 0x0200) >>9, //
				(hit_pattern[11] & 0x2000) >>13, //
				(hit_pattern[10] & 0x0002) >>1, //
				(hit_pattern[10] & 0x0020) >>5, //
				(hit_pattern[10] & 0x0200) >>9, //
				(hit_pattern[10] & 0x2000) >>13 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0001) >>0, //
				(hit_pattern[14] & 0x0010) >>4, //
				(hit_pattern[14] & 0x0100) >>8, //
				(hit_pattern[14] & 0x1000) >>12, //
				(hit_pattern[13] & 0x0001) >>0, //
				(hit_pattern[13] & 0x0010) >>4, //
				(hit_pattern[13] & 0x0100) >>8, //
				(hit_pattern[13] & 0x1000) >>12, //
				(hit_pattern[12] & 0x0001) >>0, //
				(hit_pattern[12] & 0x0010) >>4, //
				(hit_pattern[12] & 0x0100) >>8, //
				(hit_pattern[12] & 0x1000) >>12, //
				(hit_pattern[11] & 0x0001) >>0, //
				(hit_pattern[11] & 0x0010) >>4, //
				(hit_pattern[11] & 0x0100) >>8, //
				(hit_pattern[11] & 0x1000) >>12, //
				(hit_pattern[10] & 0x0001) >>0, //
				(hit_pattern[10] & 0x0010) >>4, //
				(hit_pattern[10] & 0x0100) >>8, //
				(hit_pattern[10] & 0x1000) >>12 //
				);
				printf("\n");
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0008) >>3, //
				(hit_pattern[9] & 0x0080) >>7, //
				(hit_pattern[9] & 0x0800) >>11, //
				(hit_pattern[9] & 0x8000) >>15, //
				(hit_pattern[8] & 0x0008) >>3, //
				(hit_pattern[8] & 0x0080) >>7, //
				(hit_pattern[8] & 0x0800) >>11, //
				(hit_pattern[8] & 0x8000) >>15, //
				(hit_pattern[7] & 0x0008) >>3, //
				(hit_pattern[7] & 0x0080) >>7, //
				(hit_pattern[7] & 0x0800) >>11, //
				(hit_pattern[7] & 0x8000) >>15, //
				(hit_pattern[6] & 0x0008) >>3, //
				(hit_pattern[6] & 0x0080) >>7, //
				(hit_pattern[6] & 0x0800) >>11, //
				(hit_pattern[6] & 0x8000) >>15, //
				(hit_pattern[5] & 0x0008) >>3, //
				(hit_pattern[5] & 0x0080) >>7, //
				(hit_pattern[5] & 0x0800) >>11, //
				(hit_pattern[5] & 0x8000) >>15 //
				);
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0004) >>2, //
				(hit_pattern[9] & 0x0040) >>6, //
				(hit_pattern[9] & 0x0400) >>10, //
				(hit_pattern[9] & 0x4000) >>14, //
				(hit_pattern[8] & 0x0004) >>2, //
				(hit_pattern[8] & 0x0040) >>6, //
				(hit_pattern[8] & 0x0400) >>10, //
				(hit_pattern[8] & 0x4000) >>14, //
				(hit_pattern[7] & 0x0004) >>2, //
				(hit_pattern[7] & 0x0040) >>6, //
				(hit_pattern[7] & 0x0400) >>10, //
				(hit_pattern[7] & 0x4000) >>14, //
				(hit_pattern[6] & 0x0004) >>2, //
				(hit_pattern[6] & 0x0040) >>6, //
				(hit_pattern[6] & 0x0400) >>10, //
				(hit_pattern[6] & 0x4000) >>14, //
				(hit_pattern[5] & 0x0004) >>2, //
				(hit_pattern[5] & 0x0040) >>6, //
				(hit_pattern[5] & 0x0400) >>10, //
				(hit_pattern[5] & 0x4000) >>14 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0002) >>1, //
				(hit_pattern[9] & 0x0020) >>5, //
				(hit_pattern[9] & 0x0200) >>9, //
				(hit_pattern[9] & 0x2000) >>13, //365
				(hit_pattern[8] & 0x0002) >>1, //
				(hit_pattern[8] & 0x0020) >>5, //
				(hit_pattern[8] & 0x0200) >>9, //
				(hit_pattern[8] & 0x2000) >>13, //
				(hit_pattern[7] & 0x0002) >>1, //
				(hit_pattern[7] & 0x0020) >>5, //
				(hit_pattern[7] & 0x0200) >>9, //
				(hit_pattern[7] & 0x2000) >>13, //
				(hit_pattern[6] & 0x0002) >>1, //
				(hit_pattern[6] & 0x0020) >>5, //
				(hit_pattern[6] & 0x0200) >>9, //
				(hit_pattern[6] & 0x2000) >>13, //
				(hit_pattern[5] & 0x0002) >>1, //
				(hit_pattern[5] & 0x0020) >>5, //
				(hit_pattern[5] & 0x0200) >>9, //
				(hit_pattern[5] & 0x2000) >>13 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0001) >>0, //
				(hit_pattern[9] & 0x0010) >>4, //
				(hit_pattern[9] & 0x0100) >>8, //
				(hit_pattern[9] & 0x1000) >>12, //
				(hit_pattern[8] & 0x0001) >>0, //
				(hit_pattern[8] & 0x0010) >>4, //
				(hit_pattern[8] & 0x0100) >>8, //
				(hit_pattern[8] & 0x1000) >>12, //
				(hit_pattern[7] & 0x0001) >>0, //
				(hit_pattern[7] & 0x0010) >>4, //
				(hit_pattern[7] & 0x0100) >>8, //
				(hit_pattern[7] & 0x1000) >>12, //
				(hit_pattern[6] & 0x0001) >>0, //
				(hit_pattern[6] & 0x0010) >>4, //
				(hit_pattern[6] & 0x0100) >>8, //
				(hit_pattern[6] & 0x1000) >>12, //
				(hit_pattern[5] & 0x0001) >>0, //
				(hit_pattern[5] & 0x0010) >>4, //
				(hit_pattern[5] & 0x0100) >>8, //
				(hit_pattern[5] & 0x1000) >>12 //
				);
				printf("\n");
			
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0008) >>3, //
				(hit_pattern[4] & 0x0080) >>7, //
				(hit_pattern[4] & 0x0800) >>11, //
				(hit_pattern[4] & 0x8000) >>15, //
				(hit_pattern[3] & 0x0008) >>3, //
				(hit_pattern[3] & 0x0080) >>7, //
				(hit_pattern[3] & 0x0800) >>11, //
				(hit_pattern[3] & 0x8000) >>15, //
				(hit_pattern[2] & 0x0008) >>3, //
				(hit_pattern[2] & 0x0080) >>7, //
				(hit_pattern[2] & 0x0800) >>11, //
				(hit_pattern[2] & 0x8000) >>15, //
				(hit_pattern[1] & 0x0008) >>3, //
				(hit_pattern[1] & 0x0080) >>7, //
				(hit_pattern[1] & 0x0800) >>11, //
				(hit_pattern[1] & 0x8000) >>15, //
				(hit_pattern[0] & 0x0008) >>3, //
				(hit_pattern[0] & 0x0080) >>7, //
				(hit_pattern[0] & 0x0800) >>11, //
				(hit_pattern[0] & 0x8000) >>15 //
				);
			printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0004) >>2, //
				(hit_pattern[4] & 0x0040) >>6, //
				(hit_pattern[4] & 0x0400) >>10, //
				(hit_pattern[4] & 0x4000) >>14, //
				(hit_pattern[3] & 0x0004) >>2, //
				(hit_pattern[3] & 0x0040) >>6, //
				(hit_pattern[3] & 0x0400) >>10, //
				(hit_pattern[3] & 0x4000) >>14, //
				(hit_pattern[2] & 0x0004) >>2, //
				(hit_pattern[2] & 0x0040) >>6, //
				(hit_pattern[2] & 0x0400) >>10, //
				(hit_pattern[2] & 0x4000) >>14, //
				(hit_pattern[1] & 0x0004) >>2, //
				(hit_pattern[1] & 0x0040) >>6, //
				(hit_pattern[1] & 0x0400) >>10, //
				(hit_pattern[1] & 0x4000) >>14, //
				(hit_pattern[0] & 0x0004) >>2, //
				(hit_pattern[0] & 0x0040) >>6, //
				(hit_pattern[0] & 0x0400) >>10, //
				(hit_pattern[0] & 0x4000) >>14 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0002) >>1, //
				(hit_pattern[4] & 0x0020) >>5, //
				(hit_pattern[4] & 0x0200) >>9, //
				(hit_pattern[4] & 0x2000) >>13, //365
				(hit_pattern[3] & 0x0002) >>1, //
				(hit_pattern[3] & 0x0020) >>5, //
				(hit_pattern[3] & 0x0200) >>9, //
				(hit_pattern[3] & 0x2000) >>13, //
				(hit_pattern[2] & 0x0002) >>1, //
				(hit_pattern[2] & 0x0020) >>5, //
				(hit_pattern[2] & 0x0200) >>9, //
				(hit_pattern[2] & 0x2000) >>13, //
				(hit_pattern[1] & 0x0002) >>1, //
				(hit_pattern[1] & 0x0020) >>5, //
				(hit_pattern[1] & 0x0200) >>9, //
				(hit_pattern[1] & 0x2000) >>13, //
				(hit_pattern[0] & 0x0002) >>1, //
				(hit_pattern[0] & 0x0020) >>5, //
				(hit_pattern[0] & 0x0200) >>9, //
				(hit_pattern[0] & 0x2000) >>13 //
				);
				
				printf(" %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0001) >>0, //
				(hit_pattern[4] & 0x0010) >>4, //
				(hit_pattern[4] & 0x0100) >>8, //
				(hit_pattern[4] & 0x1000) >>12, //
				(hit_pattern[3] & 0x0001) >>0, //
				(hit_pattern[3] & 0x0010) >>4, //
				(hit_pattern[3] & 0x0100) >>8, //
				(hit_pattern[3] & 0x1000) >>12, //
				(hit_pattern[2] & 0x0001) >>0, //
				(hit_pattern[2] & 0x0010) >>4, //
				(hit_pattern[2] & 0x0100) >>8, //
				(hit_pattern[2] & 0x1000) >>12, //
				(hit_pattern[1] & 0x0001) >>0, //
				(hit_pattern[1] & 0x0010) >>4, //
				(hit_pattern[1] & 0x0100) >>8, //
				(hit_pattern[1] & 0x1000) >>12, //
				(hit_pattern[0] & 0x0001) >>0, //
				(hit_pattern[0] & 0x0010) >>4, //
				(hit_pattern[0] & 0x0100) >>8, //
				(hit_pattern[0] & 0x1000) >>12 //
				);
				
			break;
		
    case '9': // Print hit pattern to file

      printf("Enter the frequency of the hit pattern recording [Hz]: ");
      //float freq;
      scanf("%f", &freq);
      
      printf("Enter the duration of the hit pattern recordingt [s]: ");
      //float dt;
      scanf("%f", &dt);

      //char sdt[32];
      sprintf(sdt, "%f", dt);

      //char sfreq[32];
      sprintf(sfreq, "%f", freq);

      N = (int)(freq * dt);
      period = 1. / freq;
      
      //int N = (int)(freq * dt);
      //float period = 1. / freq;
      
      printf("%s %0.1f %s %0.1f %s", "Hit patterns will be read for", dt, "s at a frequency of", freq, "Hz\n");
      printf("%s %d %s %0.3f %s", "Will read", N, "patterns with a period of", period, "s\n");
      printf("\n");
      
      //FILE *fptr;
      fptr = fopen("hitpattern.txt", "w");
      fprintf(fptr, "N: %d, freq: %f\n", N, freq);

      for (int step = 0; step < N; step++) {
      printf("Step: %d\n", step+1);


			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_HIT_PATTERN; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
      
      //time_t t = time(NULL);
      //struct tm tm = *localtime(&t);
      fprintf(fptr, "Step: %d\n", step+1);
      //fprintf(fptr, "Date: %d-%02d-%02d %02d:%02d:%02d\n", tm.tm_year + 1900, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min, tm.tm_sec);

      struct timespec ts;
      timespec_get(&ts, TIME_UTC);
      char buff[100];
      strftime(buff, sizeof buff, "%D %T", gmtime(&ts.tv_sec));
      fprintf(fptr, "Current time: %s.%09ld UTC\n", buff, ts.tv_nsec);
			
			for(i=0;i<8;i++){
				hit_pattern[31-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN1; //cw
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[23-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN2; //cw
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[15-i] = data[i+2];
			}
			
			spi_message[1] = SPI_READ_HIT_PATTERN3; //cw
			transfer_message(spi_message,data);
			//display_slavespi_data(data);
			
			for(i=0;i<8;i++){
				hit_pattern[7-i] = data[i+2];
			}
			
			fprintf(fptr, "\n");
			/*
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0008) >>3, //451
				(hit_pattern[28] & 0x0080) >>7, //455
				(hit_pattern[28] & 0x0800) >>11, //459
				(hit_pattern[28] & 0x8000) >>15, //463
				(hit_pattern[29] & 0x0008) >>3, //467
				(hit_pattern[29] & 0x0080) >>7, //471
				(hit_pattern[29] & 0x0800) >>11, //475
				(hit_pattern[29] & 0x8000) >>15, //479
				(hit_pattern[30] & 0x0008) >>3, //483
				(hit_pattern[30] & 0x0080) >>7, //487
				(hit_pattern[30] & 0x0800) >>11, //491
				(hit_pattern[30] & 0x8000) >>15, //495
				(hit_pattern[31] & 0x0008) >>3, //499
				(hit_pattern[31] & 0x0080) >>7, //503
				(hit_pattern[31] & 0x0800) >>11, //507
				(hit_pattern[31] & 0x8000) >>15 //511
				);
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0004) >>2, //450
				(hit_pattern[28] & 0x0040) >>6, //454
				(hit_pattern[28] & 0x0400) >>10, //458
				(hit_pattern[28] & 0x4000) >>14, //462
				(hit_pattern[29] & 0x0004) >>2, //466
				(hit_pattern[29] & 0x0040) >>6, //470
				(hit_pattern[29] & 0x0400) >>10, //474
				(hit_pattern[29] & 0x4000) >>14, //478
				(hit_pattern[30] & 0x0004) >>2, //482
				(hit_pattern[30] & 0x0040) >>6, //486
				(hit_pattern[30] & 0x0400) >>10, //490
				(hit_pattern[30] & 0x4000) >>14, //494
				(hit_pattern[31] & 0x0004) >>2, //498
				(hit_pattern[31] & 0x0040) >>6, //502
				(hit_pattern[31] & 0x0400) >>10, //506
				(hit_pattern[31] & 0x4000) >>14 //510
				);
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0002) >>1, //449
				(hit_pattern[28] & 0x0020) >>5, //453
				(hit_pattern[28] & 0x0200) >>9, //457
				(hit_pattern[28] & 0x2000) >>13, //461
				(hit_pattern[29] & 0x0002) >>1, //465
				(hit_pattern[29] & 0x0020) >>5, //469
				(hit_pattern[29] & 0x0200) >>9, //473
				(hit_pattern[29] & 0x2000) >>13, //477
				(hit_pattern[30] & 0x0002) >>1, //481
				(hit_pattern[30] & 0x0020) >>5, //485
				(hit_pattern[30] & 0x0200) >>9, //489
				(hit_pattern[30] & 0x2000) >>13, //493
				(hit_pattern[31] & 0x0002) >>1, //497
				(hit_pattern[31] & 0x0020) >>5, //501
				(hit_pattern[31] & 0x0200) >>9, //505
				(hit_pattern[31] & 0x2000) >>13 //509
				);
			printf("      %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[28] & 0x0001) >>0, //448
				(hit_pattern[28] & 0x0010) >>4, //452
				(hit_pattern[28] & 0x0100) >>8, //456
				(hit_pattern[28] & 0x1000) >>12, //460
				(hit_pattern[29] & 0x0001) >>0, //464
				(hit_pattern[29] & 0x0010) >>4, //468
				(hit_pattern[29] & 0x0100) >>8, //472
				(hit_pattern[29] & 0x1000) >>12, //476
				(hit_pattern[30] & 0x0001) >>0, //480
				(hit_pattern[30] & 0x0010) >>4, //484
				(hit_pattern[30] & 0x0100) >>8, //488
				(hit_pattern[30] & 0x1000) >>12, //492
				(hit_pattern[31] & 0x0001) >>0, //496
				(hit_pattern[31] & 0x0010) >>4, //500
				(hit_pattern[31] & 0x0100) >>8, //504
				(hit_pattern[31] & 0x1000) >>12 //508
				);
				
			printf("\n");
			*/
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0008) >>3, //
				(hit_pattern[24] & 0x0080) >>7, //
				(hit_pattern[24] & 0x0800) >>11, //
				(hit_pattern[24] & 0x8000) >>15, //367
				(hit_pattern[23] & 0x0008) >>3, //
				(hit_pattern[23] & 0x0080) >>7, //
				(hit_pattern[23] & 0x0800) >>11, //
				(hit_pattern[23] & 0x8000) >>15, //
				(hit_pattern[22] & 0x0008) >>3, //
				(hit_pattern[22] & 0x0080) >>7, //
				(hit_pattern[22] & 0x0800) >>11, //
				(hit_pattern[22] & 0x8000) >>15, //
				(hit_pattern[21] & 0x0008) >>3, //
				(hit_pattern[21] & 0x0080) >>7, //
				(hit_pattern[21] & 0x0800) >>11, //
				(hit_pattern[21] & 0x8000) >>15, //
				(hit_pattern[20] & 0x0008) >>3, //
				(hit_pattern[20] & 0x0080) >>7, //
				(hit_pattern[20] & 0x0800) >>11, //
				(hit_pattern[20] & 0x8000) >>15 //
				);
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0004) >>2, //
				(hit_pattern[24] & 0x0040) >>6, //
				(hit_pattern[24] & 0x0400) >>10, //
				(hit_pattern[24] & 0x4000) >>14, //366
				(hit_pattern[23] & 0x0004) >>2, //
				(hit_pattern[23] & 0x0040) >>6, //
				(hit_pattern[23] & 0x0400) >>10, //
				(hit_pattern[23] & 0x4000) >>14, //
				(hit_pattern[22] & 0x0004) >>2, //
				(hit_pattern[22] & 0x0040) >>6, //
				(hit_pattern[22] & 0x0400) >>10, //
				(hit_pattern[22] & 0x4000) >>14, //
				(hit_pattern[21] & 0x0004) >>2, //
				(hit_pattern[21] & 0x0040) >>6, //
				(hit_pattern[21] & 0x0400) >>10, //
				(hit_pattern[21] & 0x4000) >>14, //
				(hit_pattern[20] & 0x0004) >>2, //
				(hit_pattern[20] & 0x0040) >>6, //
				(hit_pattern[20] & 0x0400) >>10, //
				(hit_pattern[20] & 0x4000) >>14 //
				);
				
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0002) >>1, //
				(hit_pattern[24] & 0x0020) >>5, //
				(hit_pattern[24] & 0x0200) >>9, //
				(hit_pattern[24] & 0x2000) >>13, //365
				(hit_pattern[23] & 0x0002) >>1, //
				(hit_pattern[23] & 0x0020) >>5, //
				(hit_pattern[23] & 0x0200) >>9, //
				(hit_pattern[23] & 0x2000) >>13, //
				(hit_pattern[22] & 0x0002) >>1, //
				(hit_pattern[22] & 0x0020) >>5, //
				(hit_pattern[22] & 0x0200) >>9, //
				(hit_pattern[22] & 0x2000) >>13, //
				(hit_pattern[21] & 0x0002) >>1, //
				(hit_pattern[21] & 0x0020) >>5, //
				(hit_pattern[21] & 0x0200) >>9, //
				(hit_pattern[21] & 0x2000) >>13, //
				(hit_pattern[20] & 0x0002) >>1, //
				(hit_pattern[20] & 0x0020) >>5, //
				(hit_pattern[20] & 0x0200) >>9, //
				(hit_pattern[20] & 0x2000) >>13 //
				);
				
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[24] & 0x0001) >>0, //352
				(hit_pattern[24] & 0x0010) >>4, //356
				(hit_pattern[24] & 0x0100) >>8, //360
				(hit_pattern[24] & 0x1000) >>12, //365
				(hit_pattern[23] & 0x0001) >>0, //
				(hit_pattern[23] & 0x0010) >>4, //
				(hit_pattern[23] & 0x0100) >>8, //
				(hit_pattern[23] & 0x1000) >>12, //
				(hit_pattern[22] & 0x0001) >>0, //
				(hit_pattern[22] & 0x0010) >>4, //
				(hit_pattern[22] & 0x0100) >>8, //
				(hit_pattern[22] & 0x1000) >>12, //
				(hit_pattern[21] & 0x0001) >>0, //
				(hit_pattern[21] & 0x0010) >>4, //
				(hit_pattern[21] & 0x0100) >>8, //
				(hit_pattern[21] & 0x1000) >>12, //
				(hit_pattern[20] & 0x0001) >>0, //
				(hit_pattern[20] & 0x0010) >>4, //
				(hit_pattern[20] & 0x0100) >>8, //
				(hit_pattern[20] & 0x1000) >>12 //
				);
				
				fprintf(fptr,"\n");
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0008) >>3, //
				(hit_pattern[19] & 0x0080) >>7, //
				(hit_pattern[19] & 0x0800) >>11, //
				(hit_pattern[19] & 0x8000) >>15, //
				(hit_pattern[18] & 0x0008) >>3, //
				(hit_pattern[18] & 0x0080) >>7, //
				(hit_pattern[18] & 0x0800) >>11, //
				(hit_pattern[18] & 0x8000) >>15, //
				(hit_pattern[17] & 0x0008) >>3, //
				(hit_pattern[17] & 0x0080) >>7, //
				(hit_pattern[17] & 0x0800) >>11, //
				(hit_pattern[17] & 0x8000) >>15, //
				(hit_pattern[16] & 0x0008) >>3, //
				(hit_pattern[16] & 0x0080) >>7, //
				(hit_pattern[16] & 0x0800) >>11, //
				(hit_pattern[16] & 0x8000) >>15, //
				(hit_pattern[15] & 0x0008) >>3, //
				(hit_pattern[15] & 0x0080) >>7, //
				(hit_pattern[15] & 0x0800) >>11, //
				(hit_pattern[15] & 0x8000) >>15 //
				);
			fprintf(fptr," %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0004) >>2, //
				(hit_pattern[19] & 0x0040) >>6, //
				(hit_pattern[19] & 0x0400) >>10, //
				(hit_pattern[19] & 0x4000) >>14, //
				(hit_pattern[18] & 0x0004) >>2, //
				(hit_pattern[18] & 0x0040) >>6, //
				(hit_pattern[18] & 0x0400) >>10, //
				(hit_pattern[18] & 0x4000) >>14, //
				(hit_pattern[17] & 0x0004) >>2, //
				(hit_pattern[17] & 0x0040) >>6, //
				(hit_pattern[17] & 0x0400) >>10, //
				(hit_pattern[17] & 0x4000) >>14, //
				(hit_pattern[16] & 0x0004) >>2, //
				(hit_pattern[16] & 0x0040) >>6, //
				(hit_pattern[16] & 0x0400) >>10, //
				(hit_pattern[16] & 0x4000) >>14, //
				(hit_pattern[15] & 0x0004) >>2, //
				(hit_pattern[15] & 0x0040) >>6, //
				(hit_pattern[15] & 0x0400) >>10, //
				(hit_pattern[15] & 0x4000) >>14 //
				);
				
				fprintf(fptr," %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0002) >>1, //
				(hit_pattern[19] & 0x0020) >>5, //
				(hit_pattern[19] & 0x0200) >>9, //
				(hit_pattern[19] & 0x2000) >>13, //365
				(hit_pattern[18] & 0x0002) >>1, //
				(hit_pattern[18] & 0x0020) >>5, //
				(hit_pattern[18] & 0x0200) >>9, //
				(hit_pattern[18] & 0x2000) >>13, //
				(hit_pattern[17] & 0x0002) >>1, //
				(hit_pattern[17] & 0x0020) >>5, //
				(hit_pattern[17] & 0x0200) >>9, //
				(hit_pattern[17] & 0x2000) >>13, //
				(hit_pattern[16] & 0x0002) >>1, //
				(hit_pattern[16] & 0x0020) >>5, //
				(hit_pattern[16] & 0x0200) >>9, //
				(hit_pattern[16] & 0x2000) >>13, //
				(hit_pattern[15] & 0x0002) >>1, //
				(hit_pattern[15] & 0x0020) >>5, //
				(hit_pattern[15] & 0x0200) >>9, //
				(hit_pattern[15] & 0x2000) >>13 //
				);
				
				fprintf(fptr," %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[19] & 0x0001) >>0, //
				(hit_pattern[19] & 0x0010) >>4, //
				(hit_pattern[19] & 0x0100) >>8, //
				(hit_pattern[19] & 0x1000) >>12, //
				(hit_pattern[18] & 0x0001) >>0, //
				(hit_pattern[18] & 0x0010) >>4, //
				(hit_pattern[18] & 0x0100) >>8, //
				(hit_pattern[18] & 0x1000) >>12, //
				(hit_pattern[17] & 0x0001) >>0, //
				(hit_pattern[17] & 0x0010) >>4, //
				(hit_pattern[17] & 0x0100) >>8, //
				(hit_pattern[17] & 0x1000) >>12, //
				(hit_pattern[16] & 0x0001) >>0, //
				(hit_pattern[16] & 0x0010) >>4, //
				(hit_pattern[16] & 0x0100) >>8, //
				(hit_pattern[16] & 0x1000) >>12, //
				(hit_pattern[15] & 0x0001) >>0, //
				(hit_pattern[15] & 0x0010) >>4, //
				(hit_pattern[15] & 0x0100) >>8, //
				(hit_pattern[15] & 0x1000) >>12 //
				);
				fprintf(fptr, "\n");
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0008) >>3, //
				(hit_pattern[14] & 0x0080) >>7, //
				(hit_pattern[14] & 0x0800) >>11, //
				(hit_pattern[14] & 0x8000) >>15, //
				(hit_pattern[13] & 0x0008) >>3, //
				(hit_pattern[13] & 0x0080) >>7, //
				(hit_pattern[13] & 0x0800) >>11, //
				(hit_pattern[13] & 0x8000) >>15, //
				(hit_pattern[12] & 0x0008) >>3, //
				(hit_pattern[12] & 0x0080) >>7, //
				(hit_pattern[12] & 0x0800) >>11, //
				(hit_pattern[12] & 0x8000) >>15, //
				(hit_pattern[11] & 0x0008) >>3, //
				(hit_pattern[11] & 0x0080) >>7, //
				(hit_pattern[11] & 0x0800) >>11, //
				(hit_pattern[11] & 0x8000) >>15, //
				(hit_pattern[10] & 0x0008) >>3, //
				(hit_pattern[10] & 0x0080) >>7, //
				(hit_pattern[10] & 0x0800) >>11, //
				(hit_pattern[10] & 0x8000) >>15 //
				);
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0004) >>2, //
				(hit_pattern[14] & 0x0040) >>6, //
				(hit_pattern[14] & 0x0400) >>10, //
				(hit_pattern[14] & 0x4000) >>14, //
				(hit_pattern[13] & 0x0004) >>2, //
				(hit_pattern[13] & 0x0040) >>6, //
				(hit_pattern[13] & 0x0400) >>10, //
				(hit_pattern[13] & 0x4000) >>14, //
				(hit_pattern[12] & 0x0004) >>2, //
				(hit_pattern[12] & 0x0040) >>6, //
				(hit_pattern[12] & 0x0400) >>10, //
				(hit_pattern[12] & 0x4000) >>14, //
				(hit_pattern[11] & 0x0004) >>2, //
				(hit_pattern[11] & 0x0040) >>6, //
				(hit_pattern[11] & 0x0400) >>10, //
				(hit_pattern[11] & 0x4000) >>14, //
				(hit_pattern[10] & 0x0004) >>2, //
				(hit_pattern[10] & 0x0040) >>6, //
				(hit_pattern[10] & 0x0400) >>10, //
				(hit_pattern[10] & 0x4000) >>14 //
				);
				
				fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0002) >>1, //
				(hit_pattern[14] & 0x0020) >>5, //
				(hit_pattern[14] & 0x0200) >>9, //
				(hit_pattern[14] & 0x2000) >>13, //365
				(hit_pattern[13] & 0x0002) >>1, //
				(hit_pattern[13] & 0x0020) >>5, //
				(hit_pattern[13] & 0x0200) >>9, //
				(hit_pattern[13] & 0x2000) >>13, //
				(hit_pattern[12] & 0x0002) >>1, //
				(hit_pattern[12] & 0x0020) >>5, //
				(hit_pattern[12] & 0x0200) >>9, //
				(hit_pattern[12] & 0x2000) >>13, //
				(hit_pattern[11] & 0x0002) >>1, //
				(hit_pattern[11] & 0x0020) >>5, //
				(hit_pattern[11] & 0x0200) >>9, //
				(hit_pattern[11] & 0x2000) >>13, //
				(hit_pattern[10] & 0x0002) >>1, //
				(hit_pattern[10] & 0x0020) >>5, //
				(hit_pattern[10] & 0x0200) >>9, //
				(hit_pattern[10] & 0x2000) >>13 //
				);
				
				fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[14] & 0x0001) >>0, //
				(hit_pattern[14] & 0x0010) >>4, //
				(hit_pattern[14] & 0x0100) >>8, //
				(hit_pattern[14] & 0x1000) >>12, //
				(hit_pattern[13] & 0x0001) >>0, //
				(hit_pattern[13] & 0x0010) >>4, //
				(hit_pattern[13] & 0x0100) >>8, //
				(hit_pattern[13] & 0x1000) >>12, //
				(hit_pattern[12] & 0x0001) >>0, //
				(hit_pattern[12] & 0x0010) >>4, //
				(hit_pattern[12] & 0x0100) >>8, //
				(hit_pattern[12] & 0x1000) >>12, //
				(hit_pattern[11] & 0x0001) >>0, //
				(hit_pattern[11] & 0x0010) >>4, //
				(hit_pattern[11] & 0x0100) >>8, //
				(hit_pattern[11] & 0x1000) >>12, //
				(hit_pattern[10] & 0x0001) >>0, //
				(hit_pattern[10] & 0x0010) >>4, //
				(hit_pattern[10] & 0x0100) >>8, //
				(hit_pattern[10] & 0x1000) >>12 //
				);
				fprintf(fptr, "\n");
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0008) >>3, //
				(hit_pattern[9] & 0x0080) >>7, //
				(hit_pattern[9] & 0x0800) >>11, //
				(hit_pattern[9] & 0x8000) >>15, //
				(hit_pattern[8] & 0x0008) >>3, //
				(hit_pattern[8] & 0x0080) >>7, //
				(hit_pattern[8] & 0x0800) >>11, //
				(hit_pattern[8] & 0x8000) >>15, //
				(hit_pattern[7] & 0x0008) >>3, //
				(hit_pattern[7] & 0x0080) >>7, //
				(hit_pattern[7] & 0x0800) >>11, //
				(hit_pattern[7] & 0x8000) >>15, //
				(hit_pattern[6] & 0x0008) >>3, //
				(hit_pattern[6] & 0x0080) >>7, //
				(hit_pattern[6] & 0x0800) >>11, //
				(hit_pattern[6] & 0x8000) >>15, //
				(hit_pattern[5] & 0x0008) >>3, //
				(hit_pattern[5] & 0x0080) >>7, //
				(hit_pattern[5] & 0x0800) >>11, //
				(hit_pattern[5] & 0x8000) >>15 //
				);
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0004) >>2, //
				(hit_pattern[9] & 0x0040) >>6, //
				(hit_pattern[9] & 0x0400) >>10, //
				(hit_pattern[9] & 0x4000) >>14, //
				(hit_pattern[8] & 0x0004) >>2, //
				(hit_pattern[8] & 0x0040) >>6, //
				(hit_pattern[8] & 0x0400) >>10, //
				(hit_pattern[8] & 0x4000) >>14, //
				(hit_pattern[7] & 0x0004) >>2, //
				(hit_pattern[7] & 0x0040) >>6, //
				(hit_pattern[7] & 0x0400) >>10, //
				(hit_pattern[7] & 0x4000) >>14, //
				(hit_pattern[6] & 0x0004) >>2, //
				(hit_pattern[6] & 0x0040) >>6, //
				(hit_pattern[6] & 0x0400) >>10, //
				(hit_pattern[6] & 0x4000) >>14, //
				(hit_pattern[5] & 0x0004) >>2, //
				(hit_pattern[5] & 0x0040) >>6, //
				(hit_pattern[5] & 0x0400) >>10, //
				(hit_pattern[5] & 0x4000) >>14 //
				);
				
				fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0002) >>1, //
				(hit_pattern[9] & 0x0020) >>5, //
				(hit_pattern[9] & 0x0200) >>9, //
				(hit_pattern[9] & 0x2000) >>13, //365
				(hit_pattern[8] & 0x0002) >>1, //
				(hit_pattern[8] & 0x0020) >>5, //
				(hit_pattern[8] & 0x0200) >>9, //
				(hit_pattern[8] & 0x2000) >>13, //
				(hit_pattern[7] & 0x0002) >>1, //
				(hit_pattern[7] & 0x0020) >>5, //
				(hit_pattern[7] & 0x0200) >>9, //
				(hit_pattern[7] & 0x2000) >>13, //
				(hit_pattern[6] & 0x0002) >>1, //
				(hit_pattern[6] & 0x0020) >>5, //
				(hit_pattern[6] & 0x0200) >>9, //
				(hit_pattern[6] & 0x2000) >>13, //
				(hit_pattern[5] & 0x0002) >>1, //
				(hit_pattern[5] & 0x0020) >>5, //
				(hit_pattern[5] & 0x0200) >>9, //
				(hit_pattern[5] & 0x2000) >>13 //
				);
				
				fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[9] & 0x0001) >>0, //
				(hit_pattern[9] & 0x0010) >>4, //
				(hit_pattern[9] & 0x0100) >>8, //
				(hit_pattern[9] & 0x1000) >>12, //
				(hit_pattern[8] & 0x0001) >>0, //
				(hit_pattern[8] & 0x0010) >>4, //
				(hit_pattern[8] & 0x0100) >>8, //
				(hit_pattern[8] & 0x1000) >>12, //
				(hit_pattern[7] & 0x0001) >>0, //
				(hit_pattern[7] & 0x0010) >>4, //
				(hit_pattern[7] & 0x0100) >>8, //
				(hit_pattern[7] & 0x1000) >>12, //
				(hit_pattern[6] & 0x0001) >>0, //
				(hit_pattern[6] & 0x0010) >>4, //
				(hit_pattern[6] & 0x0100) >>8, //
				(hit_pattern[6] & 0x1000) >>12, //
				(hit_pattern[5] & 0x0001) >>0, //
				(hit_pattern[5] & 0x0010) >>4, //
				(hit_pattern[5] & 0x0100) >>8, //
				(hit_pattern[5] & 0x1000) >>12 //
				);
				fprintf(fptr, "\n");
			
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0008) >>3, //
				(hit_pattern[4] & 0x0080) >>7, //
				(hit_pattern[4] & 0x0800) >>11, //
				(hit_pattern[4] & 0x8000) >>15, //
				(hit_pattern[3] & 0x0008) >>3, //
				(hit_pattern[3] & 0x0080) >>7, //
				(hit_pattern[3] & 0x0800) >>11, //
				(hit_pattern[3] & 0x8000) >>15, //
				(hit_pattern[2] & 0x0008) >>3, //
				(hit_pattern[2] & 0x0080) >>7, //
				(hit_pattern[2] & 0x0800) >>11, //
				(hit_pattern[2] & 0x8000) >>15, //
				(hit_pattern[1] & 0x0008) >>3, //
				(hit_pattern[1] & 0x0080) >>7, //
				(hit_pattern[1] & 0x0800) >>11, //
				(hit_pattern[1] & 0x8000) >>15, //
				(hit_pattern[0] & 0x0008) >>3, //
				(hit_pattern[0] & 0x0080) >>7, //
				(hit_pattern[0] & 0x0800) >>11, //
				(hit_pattern[0] & 0x8000) >>15 //
				);
			fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0004) >>2, //
				(hit_pattern[4] & 0x0040) >>6, //
				(hit_pattern[4] & 0x0400) >>10, //
				(hit_pattern[4] & 0x4000) >>14, //
				(hit_pattern[3] & 0x0004) >>2, //
				(hit_pattern[3] & 0x0040) >>6, //
				(hit_pattern[3] & 0x0400) >>10, //
				(hit_pattern[3] & 0x4000) >>14, //
				(hit_pattern[2] & 0x0004) >>2, //
				(hit_pattern[2] & 0x0040) >>6, //
				(hit_pattern[2] & 0x0400) >>10, //
				(hit_pattern[2] & 0x4000) >>14, //
				(hit_pattern[1] & 0x0004) >>2, //
				(hit_pattern[1] & 0x0040) >>6, //
				(hit_pattern[1] & 0x0400) >>10, //
				(hit_pattern[1] & 0x4000) >>14, //
				(hit_pattern[0] & 0x0004) >>2, //
				(hit_pattern[0] & 0x0040) >>6, //
				(hit_pattern[0] & 0x0400) >>10, //
				(hit_pattern[0] & 0x4000) >>14 //
				);
				
				fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0002) >>1, //
				(hit_pattern[4] & 0x0020) >>5, //
				(hit_pattern[4] & 0x0200) >>9, //
				(hit_pattern[4] & 0x2000) >>13, //365
				(hit_pattern[3] & 0x0002) >>1, //
				(hit_pattern[3] & 0x0020) >>5, //
				(hit_pattern[3] & 0x0200) >>9, //
				(hit_pattern[3] & 0x2000) >>13, //
				(hit_pattern[2] & 0x0002) >>1, //
				(hit_pattern[2] & 0x0020) >>5, //
				(hit_pattern[2] & 0x0200) >>9, //
				(hit_pattern[2] & 0x2000) >>13, //
				(hit_pattern[1] & 0x0002) >>1, //
				(hit_pattern[1] & 0x0020) >>5, //
				(hit_pattern[1] & 0x0200) >>9, //
				(hit_pattern[1] & 0x2000) >>13, //
				(hit_pattern[0] & 0x0002) >>1, //
				(hit_pattern[0] & 0x0020) >>5, //
				(hit_pattern[0] & 0x0200) >>9, //
				(hit_pattern[0] & 0x2000) >>13 //
				);
				
				fprintf(fptr, " %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x %x%x%x%x\n", 
				(hit_pattern[4] & 0x0001) >>0, //
				(hit_pattern[4] & 0x0010) >>4, //
				(hit_pattern[4] & 0x0100) >>8, //
				(hit_pattern[4] & 0x1000) >>12, //
				(hit_pattern[3] & 0x0001) >>0, //
				(hit_pattern[3] & 0x0010) >>4, //
				(hit_pattern[3] & 0x0100) >>8, //
				(hit_pattern[3] & 0x1000) >>12, //
				(hit_pattern[2] & 0x0001) >>0, //
				(hit_pattern[2] & 0x0010) >>4, //
				(hit_pattern[2] & 0x0100) >>8, //
				(hit_pattern[2] & 0x1000) >>12, //
				(hit_pattern[1] & 0x0001) >>0, //
				(hit_pattern[1] & 0x0010) >>4, //
				(hit_pattern[1] & 0x0100) >>8, //
				(hit_pattern[1] & 0x1000) >>12, //
				(hit_pattern[0] & 0x0001) >>0, //
				(hit_pattern[0] & 0x0010) >>4, //
				(hit_pattern[0] & 0x0100) >>8, //
				(hit_pattern[0] & 0x1000) >>12 //
				);

      double period_int;
      double period_frac = modf(period, &period_int);

      if ((int) period_int > 0) {
        s_sleep((int) period_int);
      }

      float period_frac_ms = period_frac * 1000;

      if ((int) period_frac_ms > 0) {
        ms_sleep((int) period_frac_ms);
      }

      }
			
      fclose(fptr);
      printf("Closing hit pattern file\n\n");
	
			break;
    
    case '$': // Print hit pattern to binary file

      printf("Enter the frequency of the hit pattern recording [Hz]: ");
      //float freq;
      scanf("%f", &freq);
      
      printf("Enter the duration of the hit pattern recordingt [s]: ");
      //float dt;
      scanf("%f", &dt);

      //char sdt[32];
      sprintf(sdt, "%f", dt);

      //char sfreq[32];
      sprintf(sfreq, "%f", freq);

      N = (int)(freq * dt);
      period = 1. / freq;
      
      printf("%s %0.1f %s %0.1f %s", "Hit patterns will be read for", dt, "s at a frequency of", freq, "Hz\n");
      printf("%s %d %s %0.3f %s", "Will read", N, "patterns with a period of", period, "s\n");
      printf("\n");

      //FILE *fptr;
      fptr = fopen("hitpattern.bin", "wb");
      fwrite(&N, sizeof(N), 1, fptr); // write number of frames to binary file
      fwrite(&freq, sizeof(freq), 1, fptr); // write sampling freq to binary file

      for (int step = 0; step < N; step++) {
      printf("Step: %d\n", step+1);

			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_HIT_PATTERN; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
      fwrite(data,sizeof(data),1, fptr); // write data to binary file

      // Write the step number to the binary file
      fwrite(&step,sizeof(step),1, fptr); // write data to binary file
      
      struct timespec ts;
      timespec_get(&ts, TIME_UTC);
      char buff[100];
      
      //struct timespec ts;
      //timespec_get(&ts, TIME_UTC);
      //char buff[100];
      //strftime(buff, sizeof buff, "%D %T", gmtime(&ts.tv_sec));
      //fprintf(fptr, "Current time: %s.%09ld UTC\n", buff, ts.tv_nsec);

      // Write the time to the binary file
      strftime(buff, sizeof(buff), "%D %T", gmtime(&ts.tv_sec));
      fwrite(buff,sizeof(buff),1, fptr); // write data to binary file
      fwrite(&ts.tv_nsec,sizeof(ts.tv_nsec),1, fptr); // write data to binary file

			spi_message[1] = SPI_READ_HIT_PATTERN1; //cw
			transfer_message(spi_message,data);
      fwrite(data,sizeof(data),1, fptr); // write data to binary file
			
			spi_message[1] = SPI_READ_HIT_PATTERN2; //cw
			transfer_message(spi_message,data);
      fwrite(data,sizeof(data),1, fptr); // write data to binary file
			
			spi_message[1] = SPI_READ_HIT_PATTERN3; //cw
			transfer_message(spi_message,data);
      fwrite(data,sizeof(data),1, fptr); // write data to binary file
			
     double period_int;
     // double period_frac = modf(period, &period_int);
     double period_frac = modf(period, &period_int);

      if ((int) period_int > 0) {
        s_sleep((int) period_int);
      }

      //float 
      float period_frac_ms = period_frac * 1000;

      if ((int) period_frac_ms > 0) {
        ms_sleep((int) period_frac_ms);
      }

      }
			
      fclose(fptr);
      printf("Closing hit pattern binary file\n\n");
	
			break;
			
		case 'r': // Reset a FEE 
            printf ("Enter which FEE to reset 0-31: ");
            scanf ("%hd", &i);
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_RESET_FEE; //cw
            spi_message[2] = i;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
            break;
			
		case 's': // Setup SYNC message. Must do a SYNC before TAACK messages will be effective
			printf("Sending a SYNC message. If Target module has already been synced,\n");
			printf("this will have no affect\n\n");
			printf("Setting TYPE (01) and MODE (00) for a SYNC message\n");
			// Set TYPE and MODE for a SYNC
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_SET_TACK_TYPE_MODE; //cw
			spi_message[2] = 0x0004; // TYPE 01 MODE 00
			spi_message[3] = 0x0000;
			spi_message[4] = 0x0000;
			spi_message[5] = 0x0000;
			spi_message[6] = 0x0000;
			spi_message[7] = 0x0000;
			spi_message[8] = 0x0000;
			spi_message[9] = 0x0000;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			us_sleep(20);
			// Set a time to send the SYNC message
			printf("Setting a time when the SYNC message will be sent\n");
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_SET_TRIG_AT_TIME; //cw
			spi_message[2] = 0x0000;
			spi_message[3] = 0x0000;
			spi_message[4] = 0x0001; // A short time after 0
			spi_message[5] = 0x0000;//RichW0x0000; // ?? Need a 4 because time in message ends up one tick behind
			// A bug to be investigated in the TFPGA gate array HDL. Also the time has to have 3 LSBs 000
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			us_sleep(20);
			// Reset the nsTimer
			printf("Reseting the nsTimer to 0\n");
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = RESET_TRIGGER_COUNT_AND_NSTIMER; //cw
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			us_sleep(20);
			// The TFPGA will sned the SYNC message when nsTimer reaches the time set above
			
			// Set TYPE and MODE back in anticipation of sending a TACK
			printf("Setting TYPE (00) and MODE (00) so subsequent message are TACKs\n");
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_SET_TACK_TYPE_MODE; //cw
			spi_message[2] = 0x0000; // TYPE 00 MODE 00
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
		 	
            break;

		case 't': // Send Trigger signal to Calibration Units
            		printf ("Sent Trigger to Cal Units\n");
            //scanf ("%hd", &i);
			int cal_runDuration;
			int cal_freq;
			printf("Specify run duration in seconds!\n");
			scanf("%d",&cal_runDuration);
			printf("Specify trigger frequency in Hz!\n");
			scanf("%d",&cal_freq);
			//int cal_msPeriod = 1000/cal_freq;
			int cal_usPeriod = 1000000/cal_freq;
			ms_sleep(1000);

			for(i=0;i<cal_runDuration*cal_freq;i++){
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_PERI_TRIG; //cw
		        spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
			us_sleep(cal_usPeriod);
			//ms_sleep(cal_msPeriod);
			}
            break;

		case 'u': // Read Power Board Status
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_RD_PWRSTATUS; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
            break;

		case 'v': // FEEs Housekeeping voltages
			trig_adcs();
			display_voltages();
            break;
		
		case 'w': // HKFPGA wrap around
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = SPI_WRAP_AROUND; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
            break;
		
        case 'x': // exit program 
            printf("\n exiting program \n\n");
            quit = 1;
            break;
			
		case 'y': // Set Array Board config 
			printf ("Enter Array Board config in hex : ");
			scanf ("%hx",&i);
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_SET_ARRAY_SERDES_CONFIG; //cw
			spi_message[2] = i;
			spi_message[3] = 0x0002;
			spi_message[4] = 0x0003;
			spi_message[5] = 0x0004;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
            break;	
		
		case 'z': // Set Tack Type and Mode 
			printf ("Enter Tack Type (0-3) : ");
			scanf ("%hx",&i);
			if (i>3) {
				printf("Not a valid entry\n");
				break;
			}
			printf ("Enter Tack Mode (0-3) : ");
			scanf ("%hx",&i2);
			if (i2>3) {
				printf("Not a valid entry\n");
				break;
			}
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_SET_TACK_TYPE_MODE; //cw
			spi_message[2] = ((i <<2) | i2);
			spi_message[3] = 0x0002;
			spi_message[4] = 0x0003;
			spi_message[5] = 0x0004;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
            break;	
			
		case '1': // DACQ Power Reset
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_DACQ1_PWR_RESET; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
            break;
			
		case '2': // DACQ Power Reset
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_DACQ2_PWR_RESET; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
            break;
			
		case '3': // Read 8 words from the DIAT
			spi_message[0] = SPI_SOM_TFPGA; //som
			spi_message[1] = SPI_READ_DIAT_WORDS; //cw
			spi_message[2] = 0X0001;
			spi_message[3] = 0X0002;
			spi_message[4] = 0X0003;
			spi_message[5] = 0X0004;
			spi_message[6] = 0x0005;
			spi_message[7] = 0x0006;
			spi_message[8] = 0x0007;
			spi_message[9] = 0x0008;			
			spi_message[10] = SPI_EOM_TFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
			
            break;
		case '4': // Reset Si5338
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_RESET_SI5338; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
            break;
		case '6': // Reset I2C bus
			spi_message[0] = SPI_SOM_HKFPGA; //som
			spi_message[1] = CW_RESET_I2C; //cw
			spi_message[2] = 0x0111;
			spi_message[3] = 0x1222;
			spi_message[4] = 0x2333;
			spi_message[5] = 0x3444;
			spi_message[6] = 0x4555;
			spi_message[7] = 0x5666;
			spi_message[8] = 0x6777;
			spi_message[9] = 0x7888;			
			spi_message[10] = SPI_EOM_HKFPGA; //not used
			transfer_message(spi_message,data);
			display_slavespi_data(data);
            break;
		
        case '\n':
            break;

        default:
            printf("\n unused key \n\n");
            break;

        }
    } // end while
    return(0);
}

/***************************************************************************************/
/***************************************************************************************/
/***************************************************************************************/

// ms_sleep - sleep for a certain number of milliseconds.
// The value of ms must be <= 999 or disaster will occur.
void ms_sleep(int ms)
{
    struct timespec ts;
    ts.tv_sec = 0;
    ts.tv_nsec = ms * 1000000L;
    nanosleep(&ts, NULL);
}

// us_sleep - sleep for a certain number of microseconds.
// The value of ms must be <= 999,999 or disaster will occur.
void us_sleep(int us)
{
    struct timespec ts;
    ts.tv_sec = 0;
    ts.tv_nsec = us * 1000L;
    nanosleep(&ts, NULL);
}

// s_sleep - sleep for a certain number of seconds.
void s_sleep(int s)
{
    struct timespec ts;
    ts.tv_sec = s;
    ts.tv_nsec = 0;
    nanosleep(&ts, NULL);
}

void tdelay(int msec){
    int i;
    long j;
    for (i = 0; i < msec; i++){
        for (j=0; j<532000; j++);
    }
    return;
}

void usdelay(int usec){
    int i;
    long j;
    for (i = 0; i < usec; i++){
        for (j=0; j<717; j++); 
    }
    return;
}

int kbhit(void) {
    /*
    ROUTINE: kbhit
    PURPOSE: Use select to see if a key has been pressed.
    RETURNS: 0 If no key has been hit, 1 If a key has been pressed.
    */
    int ret;
    fd_set rfds;
    struct timeval wait;
    wait.tv_sec  = 0;
    wait.tv_usec = 0;
    FD_ZERO(&rfds);
    FD_SET(0, &rfds);
    ret = select(1, &rfds, NULL, NULL, &wait);
    return(ret);
}

/*
	spi_tword
	J. Buckley
	8/5/15
	
	bcm2835 library (and possibly all SPI on Raspberry PI)
	assumes 8bit transfers.   This function turns two 8-bit
	transfers (write and simultaneous read) as 16-bit transfers
	(I hope)
*/
unsigned short	spi_tword(unsigned short write_word)
{
	unsigned char   write_msb ;
    unsigned char   write_lsb ;
    unsigned char read_msb ;
    unsigned char read_lsb ;
    unsigned short  tword ;
    char    tbuf[2] ;
    char    rbuf[2] ;

    tword = (write_word & 0xff00)>>8 ;
    tbuf[0]=write_msb = (unsigned char)(tword) ;
    tword = (write_word & 0x00ff) ;
    tbuf[1]=write_lsb = (unsigned char)(tword) ;

    // read_msb = bcm2835_spi_transfer(write_msb) ;
    // read_lsb = bcm2835_spi_transfer(write_lsb) ;
    bcm2835_spi_transfernb(tbuf, rbuf, 0x00000002) ;
    read_msb = rbuf[0] ;
    read_lsb = rbuf[1] ;
    tword = read_msb ;
    tword = (tword<<8)+read_lsb ;
    return(tword) ;

}

/*
	transfer_message()
	J. Buckley
	8/6/15

	Simultaneously send a message (from PI master to slave FPGA) and read
	data (from FPGA slave to PI master).  
	Format of both send message and receive data are:
	SOM word, CMD word, 8 words of data, EOM word.
	Full duplex operation makes this simultaneous transfer of bits,
	bytes and words a bit tricky.
*/ 
void transfer_message(unsigned short *message, unsigned short *pdata) {
	unsigned short dummy_word ;
	unsigned short som_word ;
	unsigned short cmd_word ;
	unsigned short eom_word ;

	// Write Start word
	// By causality, nobody is in a state to send anything back on MISO
	// so one reads a dummy word coming back from the slave to the master.
	dummy_word = spi_tword(message[0]) ;
	// Write command word
	// word sent now that a specific SPI slave knows that the following
	// command and data is meant for it.   The slave is one byte behind,
	// and sends its start of message word back to the master.  This
	// can be checked to make sure the command response makes sense.
	pdata[0] = som_word = spi_tword(message[1]) ;
	// Next send the first data word, stored in mesage[2] from master
	// to slave.  Simultaneously read out the returned command word from
	// slave to master.   Full duplex du-suck.
	pdata[1] = cmd_word = spi_tword(message[2]) ;
	// now, the next 7 words coming back are actually data, but the 
	// last message word message[9] from the 
	pdata[2] = spi_tword(message[3]);
	pdata[3] = spi_tword(message[4]);
	pdata[4] = spi_tword(message[5]);
	pdata[5] = spi_tword(message[6]);
	pdata[6] = spi_tword(message[7]);
	pdata[7] = spi_tword(message[8]);
	pdata[8] = spi_tword(message[9]);
	pdata[9] = spi_tword(0x0000); //Send null word, get 8th data word from slave
	
	// This next bit is tricky.  Since there is a phase shift of one
	// word (received from slave versus sent to slave), you might ask
	// "When I send the 11th word from master to slave, the slave is not
	// done - it still needs to send its last EOM word.  What gives?"
	// Well, it turns out before the master sends the EOM to the slave
	// it first sends out a dummy_word then sends EOM, while the slave
	// SIMULTANEOUSLY sends back its EOM - no causality problems since
	// it's just end of message.
	pdata[10] = spi_tword(message[10]);

	/*switch(som_word) {
	  case SPI_SOM_HKFPGA :
	    printf("Received HK command response: %4x\n",cmd_word) ;
	  break ;

	  case SPI_SOM_TFPGA :
	    printf("Received TRIGFPGA command response: %4x\n",cmd_word) ;
	  break ;

	  default:
	    printf("Invalid SOM: %4x, command response:%4x\n",som_word,
	     cmd_word) ;
	  break ;
	} // end switch */
}

void display_slavespi_data (unsigned short *data) {
	unsigned short i;
	printf(" SOM  CMD DW 1 DW 2 DW 3 DW 4 DW 5 DW 6 DW 7 DW 8  EOM\n");
    printf( "\033[01;34m%04x\033[0m ",data[0]);
    printf( "\033[01;33m%04x\033[0m ", data[1]);
    for (i=1; i< 9; i++){
		printf("%04x ", data[i+1]);
    }
    printf( "\033[01;34m%04x\033[0m\n", data[10]);
    return;
}

void print_slavespi_data (FILE * fptr, unsigned short *data) {
	unsigned short i;
	fprintf(fptr, " SOM  CMD DW 1 DW 2 DW 3 DW 4 DW 5 DW 6 DW 7 DW 8  EOM\n");
    //fprintf(fptr,  "\033[01;34m%04x\033[0m ",data[0]);
    //fprintf(fptr,  "\033[01;33m%04x\033[0m ", data[1]);
    fprintf(fptr,  "%04x ",data[0]);
    fprintf(fptr,  "%04x ", data[1]);
    for (i=1; i< 9; i++){
		fprintf(fptr, "%04x ", data[i+1]);
    }
    //fprintf(fptr, "\033[01;34m%04x\033[0m\n", data[10]);
    fprintf(fptr, "%04x\n", data[10]);
    return;
}

void display_fees_present (void) {
	unsigned short spi_message[11];
	unsigned short data[11];
	
	spi_message[0] = SPI_SOM_HKFPGA; //som
	spi_message[1] = CW_FEEs_PRESENT; //cw
	spi_message[2] = 0x0111;
	spi_message[3] = 0x1222;
	spi_message[4] = 0x2333;
	spi_message[5] = 0x3444;
	spi_message[6] = 0x4555;
	spi_message[7] = 0x5666;
	spi_message[8] = 0x6777;
	spi_message[9] = 0x7888;		 	
	spi_message[10] = SPI_EOM_HKFPGA; //not used
	transfer_message(spi_message,data);

	// data[2] is FEEs present J0-15
	// data[3] is FEEs present J16-31
	







	printf("%x ", (data[2] & 0x0020) >> 5); // slot j5, FPM 4-20
	printf("%x ", (data[2] & 0x0040) >> 6); // slot j6, FPM 4-21
	printf("%x ", (data[2] & 0x0080) >> 7); // slot j7, FPM 4-22
	printf("%x ", (data[2] & 0x0100) >> 8); // slot j8, FPM 4-23
	printf("%x ", (data[2] & 0x0200) >> 9); // slot j9, FPM 4-24
	printf("\n");


	printf("%x ", (data[2] & 0x0800) >> 11); // slot j11, FPM 4-15
	printf("%x ", (data[2] & 0x1000) >> 12); // slot j12, FPM 4-16
	printf("%x ", (data[2] & 0x2000) >> 13); // slot j13, FPM 4-17
	printf("%x ", (data[2] & 0x4000) >> 14); // slot j14, FPM 4-18
	printf("%x ", (data[2] & 0x8000) >> 15); // slot j15, FPM 4-19
	printf("\n");


	printf("%x ", (data[3] & 0x0002) >> 1); // slot j17, FPM 4-10
	printf("%x ", (data[3] & 0x0004) >> 2); // slot j18, FPM 4-11
	printf("%x ", (data[3] & 0x0008) >> 3); // slot j19, FPM 4-12
	printf("%x ", (data[3] & 0x0010) >> 4); // slot j20, FPM 4-13
	printf("%x ", (data[3] & 0x0020) >> 5); // slot j21, FPM 4-14
	printf("\n");


	printf("%x ", (data[3] & 0x0080) >> 7); // slot j23, FPM 4-5
	printf("%x ", (data[3] & 0x0100) >> 8); // slot j24, FPM 4-6
	printf("%x ", (data[3] & 0x0200) >> 9); // slot j25, FPM 4-7
	printf("%x ", (data[3] & 0x0400) >> 10); // slot j26, FPM 4-8
	printf("%x ", (data[3] & 0x0800) >> 11); // slot j27, FPM 4-9
	printf("\n");


	printf("%x ", (data[3] & 0x1000) >> 12); // slot j28, FPM 4-0
	printf("%x ", (data[3] & 0x2000) >> 13); // slot j29, FPM 4-1
	printf("%x ", (data[3] & 0x4000) >> 14); // slot j30, FPM 4-2
	printf("%x ", (data[3] & 0x8000) >> 15); // slot j31, FPM 4-3
	printf("%x ", (data[3] & 0x0040) >> 6);   // slot j32 has a jumper to j22, FPM 4-4
	printf("\n");
	
	// data[5] is FEE Power ON/OFF status J0-15
	// data[4] is FEE Power ON/OFF status J16-31
	return;
}

void display_nstime_trigger_count (unsigned short *data) {
    unsigned long long nstime;
    unsigned long tacks, hwtriggers;
    float rate, rate2;
//    printf("long %d  long long %d\n", sizeof(long), sizeof(long long));
    nstime = 0;
    nstime = ( ((unsigned long long) data[2] << 48) |
	       ((unsigned long long) data[3] << 32) |
	       ((unsigned long long) data[4] << 16) |
	       ((unsigned long long) data[5]      ));
    //nstime = 0x1234567890abcdef;
    tacks = ((data[6] << 16) | data[7])-1; //TFPGA adds one extra on reset
	//tacks = ((data[6] << 16) | data[7]);
    printf("nsTimer %llu ns\n", nstime);
    //printf("%llx\n", nstime);
    printf("TACK Count %lu\n", tacks);
    rate = (float) nstime/1000000000;
    rate = tacks/rate;
    printf("TACK Rate: %6.2f Hz\n", rate);
	hwtriggers = ((data[8] << 16) | data[9])-1;
	printf("Hardware Trigger Count %lu\n", hwtriggers); // 4 phases or external trigger can HW trigger
	rate2 = (float) nstime/1000000000;
	rate2 = hwtriggers/rate2;
	printf("HW Trigger Rate: %6.2f Hz\n", rate2);
	
    return;
}

void trig_adcs (void){
	unsigned short spi_message[11];
	unsigned short data[11];
	
	spi_message[0] = SPI_SOM_HKFPGA; // som
	spi_message[1] = CW_TRG_ADCS; // cw
	spi_message[2] = 0x0111;
	spi_message[3] = 0x1222;
	spi_message[4] = 0x2333;
	spi_message[5] = 0x3444;
	spi_message[6] = 0x4555;
	spi_message[7] = 0x5666;
	spi_message[8] = 0x0000;
	spi_message[9] = 0x0088;
	spi_message[10] = SPI_EOM_HKFPGA; // not used
	transfer_message(spi_message,data);// trig ADCs
	delay(100);
}

void display_voltages (void) {
    unsigned short i, voltsarray[32];
	unsigned short data[11];
    float volts[32];
	unsigned short spi_message[11];
	
	tdelay(10);
	spi_message[0] = SPI_SOM_HKFPGA; // som
	spi_message[1] = CW_RD_FEE0_V; //cw
	spi_message[2] = 0x0111;
	spi_message[3] = 0x1222;
	spi_message[4] = 0x2333;
	spi_message[5] = 0x3444;
	spi_message[6] = 0x4555;
	spi_message[7] = 0x5666;
	spi_message[8] = 0x0000;
	spi_message[9] = 0x0088;	
	spi_message[10] = SPI_EOM_HKFPGA; // not used
	transfer_message(spi_message,data);
	
    voltsarray[5]  = data[2];
	voltsarray[12] = data[3];
	voltsarray[6]  = data[4];
	voltsarray[17] = data[5];
	voltsarray[7]  = data[6];
	voltsarray[13] = data[7];
	voltsarray[11] = data[8];
	voltsarray[18] = data[9];
		
	tdelay(10);
	spi_message[1] = CW_RD_FEE8_V; //cw
	transfer_message(spi_message,data);
	
    voltsarray[4]  = data[2];
	voltsarray[10] = data[3];
	voltsarray[1]  = data[4];
	voltsarray[0]  = data[5];
	voltsarray[3]  = data[6];
	voltsarray[2]  = data[7];
	voltsarray[16] = data[8];
	voltsarray[22] = data[9];
	
	tdelay(10);
	spi_message[1] = CW_RD_FEE16_V; //cw
	transfer_message(spi_message,data);

    voltsarray[28] = data[2];
	voltsarray[24] = data[3];
	voltsarray[30] = data[4];
	voltsarray[23] = data[5];
	voltsarray[31] = data[6];
	voltsarray[29] = data[7];
	voltsarray[26] = data[8];
	voltsarray[25] = data[9];
	
	tdelay(10);
	spi_message[1] = CW_RD_FEE24_V; //cw
	transfer_message(spi_message,data);
	
    voltsarray[20] = data[2];
	voltsarray[8]  = data[3];
	voltsarray[27] = data[4];
	voltsarray[15] = data[5];
	voltsarray[9]  = data[6];
	voltsarray[19] = data[7];
	voltsarray[21] = data[8];
	voltsarray[14] = data[9];
	
    for (i=0; i< 32; i++){
		volts[i] = voltsarray[i] * 0.006158;
    }

	printf("\nFEE Volrages Should be ~12V\n\n");

	printf("%5.2f  ", volts[5]);
	printf("%5.2f  ", volts[6]);
	printf("%5.2f  ", volts[7]);
	printf("%5.2f  ", volts[8]);
	printf("%5.2f  ", volts[9]);
	printf("\n");
	
	printf("%5.2f  ", volts[11]);
	printf("%5.2f  ", volts[12]);
	printf("%5.2f  ", volts[13]);
	printf("%5.2f  ", volts[14]);
	printf("%5.2f  ", volts[15]);
	printf("\n");
	
	printf("%5.2f  ", volts[17]);
	printf("%5.2f  ", volts[18]);
	printf("%5.2f  ", volts[19]);
	printf("%5.2f  ", volts[20]);
	printf("%5.2f  ", volts[21]);
	printf("\n");
	
	printf("%5.2f  ", volts[23]);
	printf("%5.2f  ", volts[24]);
	printf("%5.2f  ", volts[25]);
	printf("%5.2f  ", volts[26]);
	printf("%5.2f  ", volts[27]);
	printf("\n");
	
	printf("%5.2f  ", volts[28]);
	printf("%5.2f  ", volts[29]);
	printf("%5.2f  ", volts[30]);
	printf("%5.2f  ", volts[31]);
	printf("%5.2f  ", volts[22]); // slot j32 and j22 are connected by a jumper
	printf("\n");
	
    return;
}

void display_currents (void) {
    unsigned short i, spi_message[11], currentarray[32];
    float amps[32];
	unsigned short data[11];
    
	tdelay(10);
	spi_message[0] = SPI_SOM_HKFPGA; // som
	spi_message[1] = CW_RD_FEE0_I; //cw
	spi_message[2] = 0x0011;
	spi_message[3] = 0x1222;
	spi_message[4] = 0x2333;
	spi_message[5] = 0x3444;
	spi_message[6] = 0x4555;
	spi_message[7] = 0x5666;
	spi_message[8] = 0x0000;
	spi_message[9] = 0x0088;	
	spi_message[10] = SPI_EOM_HKFPGA; // not used
	transfer_message(spi_message,data);

    currentarray[5]  = data[2];
	currentarray[12] = data[3];
	currentarray[6]  = data[4];
	currentarray[17] = data[5];
	currentarray[7]  = data[6];
	currentarray[13] = data[7];
	currentarray[11] = data[8];
	currentarray[18] = data[9];
	
	tdelay(10);
	spi_message[1] = CW_RD_FEE8_I; //cw
	transfer_message(spi_message,data);

    currentarray[4]  = data[2];
	currentarray[10] = data[3];
	currentarray[1]  = data[4];
	currentarray[0]  = data[5];
	currentarray[3]  = data[6];
	currentarray[2]  = data[7];
	currentarray[16] = data[8];
	currentarray[22] = data[9];
	
	tdelay(10);
	spi_message[1] = CW_RD_FEE16_I; //cw
	transfer_message(spi_message,data);

    currentarray[28] = data[2];
	currentarray[24] = data[3];
	currentarray[30] = data[4];
	currentarray[23] = data[5];
	currentarray[31] = data[6];
	currentarray[29] = data[7];
	currentarray[26] = data[8];
	currentarray[25] = data[9];
	
	tdelay(10);
	spi_message[1] = CW_RD_FEE24_I; //cw
	transfer_message(spi_message,data);
	
    currentarray[20] = data[2];
	currentarray[8]  = data[3];
	currentarray[27] = data[4];
	currentarray[15] = data[5];
	currentarray[9]  = data[6];
	currentarray[19] = data[7];
	currentarray[21] = data[8];
	currentarray[14] = data[9];	
	
    for (i=0; i< 32; i++){
		amps[i] = currentarray[i] * 0.00117;
    }

	printf("\nFEE 12 Volt Current (A)\n\n");

	printf("%5.2f  ", amps[5]);
	printf("%5.2f  ", amps[6]);
	printf("%5.2f  ", amps[7]);
	printf("%5.2f  ", amps[8]);
	printf("%5.2f  ", amps[9]);
	printf("\n");
	
	printf("%5.2f  ", amps[11]);
	printf("%5.2f  ", amps[12]);
	printf("%5.2f  ", amps[13]);
	printf("%5.2f  ", amps[14]);
	printf("%5.2f  ", amps[15]);
	printf("\n");
	
	printf("%5.2f  ", amps[17]);
	printf("%5.2f  ", amps[18]);
	printf("%5.2f  ", amps[19]);
	printf("%5.2f  ", amps[20]);
	printf("%5.2f  ", amps[21]);
	printf("\n");
	
	printf("%5.2f  ", amps[23]);
	printf("%5.2f  ", amps[24]);
	printf("%5.2f  ", amps[25]);
	printf("%5.2f  ", amps[26]);
	printf("%5.2f  ", amps[27]);
	printf("\n");
	
	printf("%5.2f  ", amps[28]);
	printf("%5.2f  ", amps[29]);
	printf("%5.2f  ", amps[30]);
	printf("%5.2f  ", amps[31]);
	printf("%5.2f  ", amps[22]); // slot j32 and j22 are connected by jumper
	printf("\n");
	
    return;
}

void display_pwrbd_hskp(void) {
	unsigned short data[11], spi_message[11];
    
	spi_message[0] = SPI_SOM_HKFPGA; // som
	spi_message[1] = CW_RD_HKPWB; //cw
	spi_message[2] = 0x0111;
	spi_message[3] = 0x1222;
	spi_message[4] = 0x2333;
	spi_message[5] = 0x3444;
	spi_message[6] = 0x4555;
	spi_message[7] = 0x5666;
	spi_message[8] = 0x0000;
	spi_message[9] = 0x0088;
	spi_message[10] = SPI_EOM_HKFPGA; // not used
	transfer_message(spi_message,data);
	
	printf(" 1V0_I  3v3_I   3V3   1V0 2V5CLK   2V5  2V5_I 2V5CLK_I\n");
	
	printf(" %5.2f" , data[2]* 0.00252); 
	printf("  %5.2f" , data[3]* 0.00126);
	printf(" %5.2f" , data[4]* 0.00123);
	printf(" %5.2f" , data[5]* 0.00122);
	printf("  %5.2f" , data[6]* 0.00122);
	printf(" %5.2f" , data[7]* 0.001225);
	printf("  %5.2f" , data[8]* 0.00252); 
	printf("    %5.2f" , data[9]* 0.00126);
	printf("\n");
}

void display_env_hskp(void) {
	unsigned short data[11], spi_message[11];
    
	spi_message[0] = SPI_SOM_HKFPGA; // som
	spi_message[1] = CW_RD_ENV; //cw
	spi_message[2] = 0x0111;
	spi_message[3] = 0x1222;
	spi_message[4] = 0x2333;
	spi_message[5] = 0x3444;
	spi_message[6] = 0x4555;
	spi_message[7] = 0x5666;
	spi_message[8] = 0x0000;
	spi_message[9] = 0x0088;
	spi_message[10] = SPI_EOM_HKFPGA; // not used
	transfer_message(spi_message,data);	
	
	printf(" DACQ1_I DACQ2_I FEE33_I FEE33_V   ENV1  ENV2  ENV3  ENV4\n");
	
	printf("   %5.2f" , data[2]* 0.00126); 
	printf("   %5.2f" , data[3]* 0.00126);
	printf("   %5.2f" , data[4]* 0.00117);
	printf("   %5.2f" , data[5]* 0.006167);
	printf("  %5.2f" , data[6]* 0.001);
	printf(" %5.2f" , data[7]* 0.001);
	printf(" %5.2f" , data[8]* 0.001); 
	printf(" %5.2f" , data[9]* 0.001);
	printf("\n");
}
