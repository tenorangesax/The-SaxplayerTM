# The-Saxplayer™
The Saxplayer™ is a device that houses a ESP32E for the microcontroller, a OLED display to see what songs are playing, 3 MX-Style keyboard switches for navigation of songs, a rotary encoder switch for adjusting the volume and navigating menus, a micro sd card slot for storing your music, and a audio jack for headphones or output to speakers! Also has a cool case I made along with it!

**[WORKING VIDEO DEMO LINK!!!](https://youtu.be/1pTQ9vNJp9s)**

**FINAL SHOTS:**

<img width="4032" height="2268" alt="IMG_7619" src="https://github.com/user-attachments/assets/b4b06943-7fac-4bd3-ac61-aa88e4c960f0" />
<img width="4032" height="3024" alt="IMG_7595" src="https://github.com/user-attachments/assets/0f017a2d-5bd0-4636-b796-8caef22a2003" />

**THE CASE:**

<img width="4032" height="3024" alt="IMG_7608" src="https://github.com/user-attachments/assets/4a2ee0c1-053b-4d9c-b71c-c71af91c6662" />
<img width="4032" height="3024" alt="IMG_7609" src="https://github.com/user-attachments/assets/9ef69578-5fcc-49c9-9d9b-4129a33604b3" />
<img width="4032" height="3024" alt="IMG_7610" src="https://github.com/user-attachments/assets/f1be34c8-3ae2-4ca0-8aab-dc8ea0c301a6" />


**3D VIEWER:**

<img width="1024" height="582" alt="Back_final" src="https://github.com/user-attachments/assets/ac5ef5e7-c8e6-4056-918b-5217ff58426f" />
<img width="1024" height="582" alt="Front_Final" src="https://github.com/user-attachments/assets/44d0cc21-26c2-4791-9414-cd3ce01752a8" />


**THE SCHEMATIC:**
<img width="1479" height="946" alt="schematic" src="https://github.com/user-attachments/assets/cb34f801-f0a0-4f20-907a-e024a205919c" />

**PCB EDITOR:**
<img width="932" height="389" alt="the components" src="https://github.com/user-attachments/assets/cc252789-7ed4-4566-85f0-8c62cc39ac86" />

**CASE MODELING:**
<img width="1285" height="663" alt="Screenshot 2026-04-18 at 4 40 20 PM" src="https://github.com/user-attachments/assets/b339ce5d-e74f-4c7a-9b3f-5e3e41a5086f" />
<img width="1115" height="701" alt="Screenshot 2026-04-18 at 4 41 53 PM" src="https://github.com/user-attachments/assets/90c0088d-9942-4e6f-b16a-170a50bcf6f0" />
<img width="1115" height="701" alt="Screenshot 2026-04-18 at 4 41 45 PM" src="https://github.com/user-attachments/assets/dbeb5399-4b97-4662-b16c-1732b34e60ba" />
<img width="1115" height="663" alt="Screenshot 2026-04-18 at 4 41 21 PM" src="https://github.com/user-attachments/assets/9a9e935e-7990-4103-b0f3-113f440e5df0" />

**BOM:**

| Id | Designator | Footprint | Quantity | Comment | Supplier and ref |
|---:|---|---|---:|---|---|
| 1 | SW2,SW1,SW3 | SW_Cherry_MX_1.00u_PCB | 3 | SW_Push |  |
| 2 | J1 | J_SD_Card-micro_socket_A | 1 | Micro_SD_Card |  |
| 3 | DS1 | LCD_OLED_128X64_1.3_I2C | 1 | OLED_128X64_1.3_I2C |  |
| 4 | R6,R5,R1,R2 | R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal | 4 | 10kΩ |  |
| 5 | J2 | Jack_3.5mm_CUI_SJ-3523-SMT_Horizontal | 1 | AudioJack3 |  |
| 6 | C3 | CP_Radial_D5.0mm_P2.00mm | 1 | 10µF |  |
| 7 | SW4 | RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm | 1 | RotaryEncoder_Switch |  |
| 8 | C5,C4 | C_Disc_D3.0mm_W1.6mm_P2.50mm | 2 | 0.1uF |  |
| 9 | C2,C1 | C_Disc_D5.0mm_W2.5mm_P5.00mm | 2 | 10µF |  |
| 10 | R3,R4 | R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal | 2 | 4.7kΩ |  |
| 11 | U1 | ESP32-DevKitC | 1 | ESP32-DevKitC |  |
