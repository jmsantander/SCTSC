The SC GUI permits an observer to monitor camera subsystem status information published by the 
camera server in a graphical format. It also permits simple control over these subsystems.

## Usage
To run the Slow Control GUI:
1. `run-server`. The server will ask for password for DACQ boards.
it's the same password as ctauser.
2. `run-slowcontrol-gui`
3. The connection LED:
   a. Green: connected to the server
   b. Black: disconnected to the server
4. Click `Initialize` 
5. Click `Fans On`.
6. Click Camera Power `ON`.
7. If Networks show less than 1 and in red color, click Backplane/reboot_dacq
   a. EHT6 and EHT6->dacq1; EHT8 and EHT9->dacq2
8. The log file will be auto saved as "date.log" in CameraSoftware/trunk/sctcamsoft/


