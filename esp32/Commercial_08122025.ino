

//KONEKTÖRLÜ MODEL, ÜRETİM KODU
//03.07.2025 - ERRORLER DE DAHİL OK
//06.08.2025 - V1.4 oldu Beklemeden sonra şarja geçme sorunu ve Unlock düzeltildi,
//Error gösterimi iyileştirildi
//07.08.2025 - Kablo hata modu düzeltildi (10 Saniye sonra reset)
//15.10.2025 - Şarj sonlandırma işlemleri iyileştirildi. Ticari versiyona göre optimizeler yapıldı. Okuma işlemleri düzenlendi errorler düzeltildi.


#include <SPI.h>
#include <MFRC522.h>
#include <SoftwareSerial.h>
#include <EEPROM.h>

// ============================================================================
// DUAL UART CONFIGURATION - v4.8.0
// Created: 2025-11-05 21:15:00 +03:00
// USB Serial (UART0): Monitoring - Continuous status updates
// GPIO Serial (UART2): Commands - Fast request/response
// ============================================================================
#define USE_DUAL_UART 1  // Set to 0 to disable GPIO UART

#if USE_DUAL_UART
  HardwareSerial SerialGPIO(2);  // UART2
  #define GPIO_UART_RX 34  // GPIO34 (input only)
  #define GPIO_UART_TX 21  // GPIO21
  #define GPIO_UART_BAUD 115200
#endif

// Monitoring: USB Serial (UART0)
#define SerialUSB Serial

// Command response timeout
#define CMD_RESPONSE_TIMEOUT_MS 100

//
void dLatchDrive(uint8_t adr, uint8_t data);
void sendLEDCommand(uint8_t* comm);
uint8_t komutBak(uint8_t* veri, uint8_t len, uint32_t* val);
uint32_t ascToDec(uint8_t* veri, uint8_t index);
void sendStat(int id = -1);
void unlock(uint16_t kekle);
void lock(uint16_t bekle);

#define EEPROM_SIZE 256

#define MYPORT_TX 22
#define MYPORT_RX 17

#define SS_PIN 33
#define RST_PIN 5

#define DLATCH_ADR0 25
#define DLATCH_ADR1 26
#define DLATCH_ADR2 27
#define DLATCH_CLK  12
#define DLATCH_DAT  14

#define MULTIP_OE   15
#define MULTIP_INP  2

#define PWM_PIN     13

#define CP_IN_PIN  39
#define PP_IN_PIN  36

#define FG_AC_PIN  4
#define FG_DC_PIN  16
//TEST PIN 259, Q5 te

#define MEM_CARD_ID 0x00  //0X3F E KADAR 16 KART ID
#define MEM_MAX_CURRENT 0x80

MFRC522 rfid(SS_PIN, RST_PIN); // Instance of the class

MFRC522::MIFARE_Key key;

// Init array that will store new NUID
byte nuidPICC[4];

//  CONTROL PILOT***
#define CP_STAT_NO_EV             0
#define CP_STAT_EV_CONNECTED      1
#define CP_STAT_CHARGING          2
#define CP_STAT_VENTILATION_NEED  3

String frompwr="";
uint16_t cpReelVal,cpTempVal;
uint8_t cpReadSay,cpStatus;
uint16_t analogSay;
uint8_t analogReady;
//uint8_t chargestart
//***
//PROXIMITY PILOT***
uint32_t ppReadVal,ppTempVal;
uint8_t ppStatus;

#define PP_STAT_ERROR   0
#define PP_STAT_NORMAL  1
//***
//PWM
uint16_t dutyYuzde;
uint8_t PWMVAL,OLDPWM,tpvm;
uint8_t pwmStatus;
//***
//KART LISTESI
#define ONAY_STAT_BEKLENIYOR    0
#define ONAY_STAT_IZIN_VERILDI  1
#define ONAY_STAT_IPTAL_ISTENDI 2

uint32_t kartIDs[10];
uint8_t kartIDValid[10];

#define MAX_KART_SAYISI 10
#define KART_BIRIM_SIZE 5  // 1 valid byte + 4 UID byte
#define MEM_CARD_ID 0      // EEPROM başlangıç adresi
uint8_t kartEklenecek;
uint32_t kartID;
uint8_t onayStatus;
//***
//KONFIGURASYON
const uint8_t DEFAULT_MAX_CURRENT = 32;
uint8_t maxCurrent;
uint8_t sessionMaxCurrent;
uint8_t cableCurrent;
const uint16_t LOCK_PULSE_MS = 500;
const uint16_t UNLOCK_PULSE_MS = 500;
//***
//USB UART COM
#define COM_STAT_RX_IDLE  0
#define COM_STAT_RX_START 1
#define COM_STAT_RX_END   2
uint8_t usbRxBuff[64],usbRxLen,usbRxStatus;

//GPIO UART COM (same protocol as USB)
#if USE_DUAL_UART
uint8_t gpioRxBuff[64],gpioRxLen,gpioRxStatus;
#endif
//***
//KOMUTLAR
#define KOMUT_LEN 6
#define KOMUT_READ_STAT   0
#define KOMUT_AUTH        1
#define KOMUT_SET_MAX_AMP 2
#define KOMUT_KILIT       3
#define STATE_MACH        4

//POWER BOADR STAT
#define POWER_BOARD_NO_ERROR  0
#define POWER_BOARD_NO_EARTH  2
#define POWER_BOARD_NO_PHASE  1

// v4.7.0: False positive filtering
#define CONSECUTIVE_FAULT_THRESHOLD 10  // 10 consecutive faults required
#define FAULT_RESET_TIMEOUT_MS 30000    // 30s timeout to reset counters
#define FAULT_MASK_WINDOW_MS 2000       // 2s mask after relay switching

//
uint8_t eskiLedKomut[4];
uint8_t TempLedStatus;
uint8_t powerBoardStat;
uint8_t phaseFaultCounter = 0;
uint8_t groundFaultCounter = 0;
uint32_t lastFaultTime = 0;
uint32_t lastRelaySwitchTime = 0;
uint8_t okuflag;
bool authEnabled = false;
bool stopRequested = false;
unsigned long lastStatTime = 0;

#define KACAK_STAT_KACAK_YOK  0
#define KACAK_STAT_KACAK_VAR  1
uint8_t kacakStat;

const PROGMEM uint8_t komutList[KOMUT_LEN][16]={

    {"READSTAT\0"},
    {"AUTH=\0"},
    {"STOP\0"},
    {"SETMAXAMP=\0"},
    {"UNLOCK\0"},
    {"LOCK\0"},

};
//***
//SARJ ISLEMLERI
//************ 03.07.25*******************
#define SARJ_STAT_IDLE                1
#define SARJ_CABLE_DETECT             2
#define EV_CONNECTED                  3
#define SARJA_HAZIR                   4
#define SARJ_STAT_SARJ_BASLADI        5
#define SARJ_STAT_SARJ_DURAKLATILDI   6
#define SARJ_STAT_SARJ_BITIR          7
#define SARJ_STAT_FAULT_HARD          8
#define HARDFAULT_END                 0



uint8_t sarjStatus;
uint32_t sarjKartID;
//***

uint16_t sendDebugSay;
uint8_t prevSarjStatus = SARJ_STAT_IDLE;


uint8_t status=0x30;
uint16_t hardFaultSay=0;
bool KabloHata=0;

uint16_t analRead;
bool RelayFlag;
uint8_t kart_flag;
uint8_t LOCKFLAG;
uint8_t MOTORFLAG;
bool BEKLEFLAG;
unsigned long tmestart;
bool err_bit_check;
bool pp1,pp2;
uint8_t valf;
EspSoftwareSerial::UART myPort;

hw_timer_t *My_timer = NULL;

uint16_t tikSay;

void IRAM_ATTR onTimer(){
  tikSay=1;
 // hardFaultSay++;
}
/**
 * Helper routine to dump a byte array as hex values to Serial.
 */
void printHex(byte *buffer, byte bufferSize) {
  for (byte i = 0; i < bufferSize; i++) {
    SerialUSB.print(buffer[i] < 0x10 ? " 0" : " ");
    SerialUSB.print(buffer[i], HEX);
  }
}


void setup() {
  delay(100);
  pinMode (RST_PIN,OUTPUT);
  uint8_t i,j,adr,tmp;
  EEPROM.begin(EEPROM_SIZE);

  // USB Serial (Monitoring)
  SerialUSB.begin(115200);
  SerialUSB.println("CSRPI Charging Station v4.8.0 - Dual UART");
  SerialUSB.println("USB: Monitoring | GPIO: Commands");

#if USE_DUAL_UART
  // GPIO UART (Commands)
  SerialGPIO.begin(GPIO_UART_BAUD, SERIAL_8N1, GPIO_UART_RX, GPIO_UART_TX);
  SerialGPIO.setTimeout(CMD_RESPONSE_TIMEOUT_MS);
  SerialUSB.printf("GPIO UART: RX=GPIO%d, TX=GPIO%d, Baud=%d\n",
                   GPIO_UART_RX, GPIO_UART_TX, GPIO_UART_BAUD);
#else
  SerialUSB.println("GPIO UART: Disabled");
#endif

  SPI.begin(); // Init SPI bus
  rfid.PCD_Init(); // Init MFRC522

  myPort.begin(9600, SWSERIAL_8N1, MYPORT_RX, MYPORT_TX, false);

  for (byte i = 0; i < 6; i++) {
    key.keyByte[i] = 0xFF;
  }

  SerialUSB.println(F("This code scan the MIFARE Classsic NUID."));
  SerialUSB.print(F("Using the following key:"));
  printHex(key.keyByte, MFRC522::MF_KEY_SIZE);

  pinMode(DLATCH_ADR0, OUTPUT);
  pinMode(DLATCH_ADR1, OUTPUT);
  pinMode(DLATCH_ADR2, OUTPUT);
  pinMode(DLATCH_CLK, OUTPUT);
  pinMode(DLATCH_DAT, OUTPUT);
  pinMode(MULTIP_OE, OUTPUT);
  pinMode(MULTIP_INP, INPUT);

  pinMode(PWM_PIN, OUTPUT);

  digitalWrite(DLATCH_CLK,HIGH);
  digitalWrite(MULTIP_OE,HIGH);

  pinMode(CP_IN_PIN, INPUT);
  pinMode(PP_IN_PIN, INPUT);


  for(uint8_t i=0; i<8; i++){
    dLatchDrive(i,0);
  }

   //old version
  // My_timer = timerBegin(0, 80, true);
  // timerAttachInterrupt(My_timer, &onTimer, true);
  // timerAlarmWrite(1000000, true);
  // timerAlarmEnable(My_timer);
  
  // new version
  // My_timer = timerBegin(0, 80, true);
  // timerAttachInterrupt(My_timer, &onTimer, true);
  // timerAlarmWrite(My_timer, 1000000 / 4 / 8, true);
  // timerAlarmEnable(My_timer);

  digitalWrite(PWM_PIN,1);
  delay(1000);

 // void kartlariYukleEEPROMdan() {
  for (int i = 0; i < MAX_KART_SAYISI; i++) {
    int adr = MEM_CARD_ID + i * KART_BIRIM_SIZE;
    kartIDValid[i] = EEPROM.read(adr);
    kartIDs[i] = 0;

    if (kartIDValid[i] == 0xAA) {
      for (int j = 0; j < 4; j++) {
        kartIDs[i] <<= 8;
        kartIDs[i] += EEPROM.read(adr + 1 + j);
      }
    }

    SerialUSB.print("Kart ");
    SerialUSB.print(i);
    SerialUSB.print(" Valid=");
    SerialUSB.print(kartIDValid[i]);
    SerialUSB.print(" ID=");
    SerialUSB.print(kartIDs[i]);
    SerialUSB.println(";");
  }

  maxCurrent = DEFAULT_MAX_CURRENT;
  sessionMaxCurrent = DEFAULT_MAX_CURRENT;
  uint8_t storedMax = EEPROM.read(MEM_MAX_CURRENT);
  if (storedMax != DEFAULT_MAX_CURRENT) {
    EEPROM.write(MEM_MAX_CURRENT, DEFAULT_MAX_CURRENT);
    EEPROM.commit();
  }
  kartEklenecek=0;
  sarjStatus=SARJ_STAT_IDLE;
  analogReady=0;
  analogSay=0;

  powerBoardStat= POWER_BOARD_NO_ERROR;
  PWMVAL=255;
 // analogSetClockDiv(1);//old version
  analogSetPinAttenuation(CP_IN_PIN,ADC_11db);


  cpStatus=CP_STAT_NO_EV;
  onayStatus=ONAY_STAT_BEKLENIYOR;
  sarjStatus=SARJ_STAT_IDLE;
  prevSarjStatus = SARJ_STAT_IDLE;

  // FIX: Ensure cable is unlocked on startup (in case of restart during charging)
  delay(200);
  unlock(500);
  LOCKFLAG=0;
  MOTORFLAG=0;

/*
  pinMode(4, OUTPUT);
  bool fgbak_bit;
  fgbak_bit=fgbak();
  if (fgbak_bit==0)SerialUSB.println("fgbak error at start-up");
*/
}

void ledIslemleri(int LedStatus){

  if(LedStatus!=TempLedStatus){
      uint8_t i,ledKomut[4];
      for(i=0;i<4;i++){ledKomut[i]=0;}

      if(LedStatus==16){ledKomut[0]=0x57;LOCKFLAG=0;MOTORFLAG=0;}   //beyaz
      if(LedStatus==1){ledKomut[0]=0x54;} //T  toprak hatası
      if(LedStatus==2){ledKomut[0]=0x4B;} //K kaçak akım hatası
      if(LedStatus==3){ledKomut[0]=0x43;} //C FAZ HATASI
      if(LedStatus==4){ledKomut[0]=0x41;} //A KABLO HATASI

      if(LedStatus==5){  //turkuaz Konektör takıldı, aracın şarjı başlatması bekleniyor
        ledKomut[0]=0x42;
        ledKomut[1]=0;
        ledKomut[2]=150;
        ledKomut[3]=150;
      }
      if(LedStatus==6){  //Mavi Otorizasyon verildi, araçtan şarj bekleniyor. lock
        ledKomut[0]=0x42;
        ledKomut[1]=10;
        ledKomut[2]=10;
        ledKomut[3]=255;
      }
      if(LedStatus==7){ledKomut[0]=0x59;} //Yeşil, şarj başladı

     if(LedStatus==8){ //Sarı, şarj duraklatıldı
        ledKomut[0]=0x42;
        ledKomut[1]=255;
        ledKomut[2]=250;
        ledKomut[3]=0;
      }

      if(LedStatus==9){ //Lila, şarj bitirildi
        ledKomut[0]=0x42;
        ledKomut[1]=255;
        ledKomut[2]=20;
        ledKomut[3]=70;
      }
 //     ledKomut[0]=0x57;
      sendLEDCommand(ledKomut);
      LedStatus=TempLedStatus;
      }
  }

  void dLatchDrive(uint8_t adr, uint8_t data){
  digitalWrite(DLATCH_CLK,HIGH);
  if(data==0){digitalWrite(DLATCH_DAT,LOW);}
  else{digitalWrite(DLATCH_DAT,HIGH);}

  if((adr & 0x01)==0){digitalWrite(DLATCH_ADR0,LOW);}
  else{digitalWrite(DLATCH_ADR0,HIGH);}
  if((adr & 0x02)==0){digitalWrite(DLATCH_ADR1,LOW);}
  else{digitalWrite(DLATCH_ADR1,HIGH);}
  if((adr & 0x04)==0){digitalWrite(DLATCH_ADR2,LOW);}
  else{digitalWrite(DLATCH_ADR2,HIGH);}

  digitalWrite(DLATCH_CLK,LOW);
  delay(1);
  digitalWrite(DLATCH_CLK,HIGH);
}

void seviyeHesapla(void){
  uint64_t pwmYuzde,voltHesap;
  pwmYuzde=PWMVAL*1000;
  pwmYuzde=pwmYuzde/255;
}

void dutyHesapIslemleri(void){
  //duty hesaplama

  if(cpStatus==CP_STAT_NO_EV){
    PWMVAL=255;
    if(cableCurrent==0){ppStatus=PP_STAT_ERROR;}
    else{ppStatus=PP_STAT_NORMAL;}
  }
  else{
    if(cableCurrent==0){
      PWMVAL=255;
      ppStatus=PP_STAT_ERROR;
    }
    else{
      ppStatus=PP_STAT_NORMAL;
      if(cableCurrent<maxCurrent){dutyYuzde=(cableCurrent*100);}
      else{dutyYuzde=(maxCurrent*100);}
        dutyYuzde=dutyYuzde/60;
        dutyYuzde=dutyYuzde*255;
        PWMVAL=dutyYuzde/100;
    }
  }
  if(PWMVAL!=OLDPWM){
    OLDPWM=PWMVAL;
    analogWrite(PWM_PIN, PWMVAL);
  }
}

//********************************************************
void CPBAK(void){
  while(analogSay<200){
    analRead=analogRead(CP_IN_PIN);
    analogSay++;
    if(analRead>cpTempVal){cpTempVal=analRead;}
  }
  analogSay=0;
  cpReelVal=cpTempVal;
  cpTempVal=0;

  if(cpReelVal>3000){cpStatus=CP_STAT_NO_EV;}
  else if(cpReelVal>2000){cpStatus=CP_STAT_EV_CONNECTED; KabloHata=0;}
  else if(cpReelVal>1500){cpStatus=CP_STAT_CHARGING; KabloHata=0;}
  else{cpStatus=CP_STAT_VENTILATION_NEED;}
}
/**************** OK 03.07.25 *****************************/
void PPBAK (void){
  while(analogSay<100){
  analRead=analogRead(PP_IN_PIN);
  analogSay++;
  ppTempVal=(ppTempVal+analRead);
  }
  ppReadVal=(ppTempVal/96); // Kalibrasyon Default=100
  analogSay=0;
  ppTempVal=0;

  if(ppReadVal>2100){cableCurrent=0;}
  else if(ppReadVal>2000){cableCurrent=6;}
  else if(ppReadVal>1800){cableCurrent=13;}
  else if(ppReadVal>1300){cableCurrent=20;}
  else if(ppReadVal>750){cableCurrent=32;}
  else if(ppReadVal>300){cableCurrent=63;}
  else{cableCurrent=0;}
//cableCurrent=30;
}
//*************************************************


void sendLEDCommand(uint8_t* comm){
  uint8_t i,test,p;
  test=0;
  p=0;
  for(i=0;i<4;i++){
    if(comm[i]==eskiLedKomut[i]){test++;}
  }
  //if(1){
  if(test<4){
    for(p=0;p<3;p++){
      myPort.write(0x4C);
      for(i=0;i<4;i++){
        myPort.write(comm[i]);
        eskiLedKomut[i]=comm[i];
      }
      delay(80);
    }
  }
}

void buzzerDriver(uint16_t sure){
  dLatchDrive(3,1);
  delay(sure);
  dLatchDrive(3,0);
}

void relayDriver(uint8_t state){
  dLatchDrive(0,state);
  lastRelaySwitchTime = millis();  // v4.7.0: Track relay switch time for fault masking
}
void unlock(uint16_t kekle){
    dLatchDrive(1,1);
    delay(kekle);
    dLatchDrive(1,0);
  }
void lock(uint16_t bekle){
    dLatchDrive(2,1);
    delay(bekle);
    dLatchDrive(2,0);
  }

void fgtest(uint16_t testet){
    dLatchDrive(5,1);
    delay(testet);
   dLatchDrive(5,0);
  }

uint8_t kartOkumaca() {
  rfid.PCD_Reset();
  rfid.PCD_Init();
  if (!rfid.PICC_IsNewCardPresent()) return 0;
  if (!rfid.PICC_ReadCardSerial()) return 0;

  MFRC522::PICC_Type piccType = rfid.PICC_GetType(rfid.uid.sak);
  if (piccType != MFRC522::PICC_TYPE_MIFARE_MINI &&
      piccType != MFRC522::PICC_TYPE_MIFARE_1K &&
      piccType != MFRC522::PICC_TYPE_MIFARE_4K) return 0;

  kartID = 0;
  for (int i = 0; i < 4; i++) {
    kartID <<= 8;
    kartID += rfid.uid.uidByte[i];
  }

  rfid.PICC_HaltA();
  rfid.PCD_StopCrypto1();
  if (okuflag > 5) buzzerDriver(200);
  return 1;
}

void kartIslemleri() {
  if (kartOkumaca() == 0) {
    okuflag++;
    if (okuflag > 200) okuflag = 200;
    return;
  }

  SerialUSB.printf("of%d\n", okuflag);

  if (kartEklenecek) {
    kartEklenecek = 0;
    bool kartVar = false;

    // Aynı kart daha önce kaydedilmiş mi?
    for (int i = 0; i < MAX_KART_SAYISI; i++) {
      if (kartIDValid[i] == 0xAA && kartIDs[i] == kartID) {
        kartVar = true;
        break;
      }
    }

    if (kartVar) {
      SerialUSB.print("<CARDEXISTS=1;>");
      return;
    }

    // Boş slot bul ve karta kaydet
    for (int i = 0; i < MAX_KART_SAYISI; i++) {
      if (kartIDValid[i] != 0xAA) {
        kartIDValid[i] = 0xAA;
        kartIDs[i] = kartID;

        uint8_t adr = MEM_CARD_ID + i * KART_BIRIM_SIZE;
        EEPROM.write(adr, 0xAA);
        for (int j = 0; j < 4; j++) {
          EEPROM.write(adr + 1 + j, rfid.uid.uidByte[j]);
        }
        EEPROM.commit();
        SerialUSB.print("<CARDADDED=1;>");
        return;
      }
    }

    SerialUSB.print("<NOCARDSPACE=1;>");
  }

  else {
    // Şarj kartı işlemleri
    if (okuflag > 2) {
      if (kart_flag == 1 && onayStatus != ONAY_STAT_IZIN_VERILDI) {
        if (cpStatus == CP_STAT_EV_CONNECTED || cpStatus == CP_STAT_CHARGING) {
          for (int i = 0; i < MAX_KART_SAYISI; i++) {
            if (kartIDValid[i] == 0xAA && kartIDs[i] == kartID) {
              sarjKartID = kartID;
              onayStatus = ONAY_STAT_IZIN_VERILDI;
              for (int j = 0; j < 3; j++) {
                buzzerDriver(100);
                delay(100);
              }
              break;
            }
          }
        }
      } else if (RelayFlag == 1 && onayStatus == ONAY_STAT_IZIN_VERILDI) {
        if (sarjKartID == kartID) {
          onayStatus = ONAY_STAT_IPTAL_ISTENDI;
        } else {
          for (int j = 0; j < 3; j++) {
            buzzerDriver(100);
            delay(100);
          }
        }
      }
      okuflag = 0;
    }
  }
}

//**************** 03.07.25 *************************************
void sarjIslemleri(void){

  switch(sarjStatus){
    case SARJ_STAT_IDLE:  //1
    LOCKFLAG=0;MOTORFLAG=0;BEKLEFLAG=0;
    kart_flag=0;
       ledIslemleri(16);
       PPBAK ();
       if(ppStatus==PP_STAT_NORMAL){
        sarjStatus=SARJ_CABLE_DETECT;
        }
   break;

    case SARJ_CABLE_DETECT:  //2
    kart_flag=1;
        PPBAK ();
        ledIslemleri(5);

        if (BEKLEFLAG==0){
          delay (400);
          BEKLEFLAG=1;
        }
       if(cpStatus==CP_STAT_EV_CONNECTED){
        sarjStatus=EV_CONNECTED;
       }
        if(ppStatus==PP_STAT_ERROR){
        sarjStatus=SARJ_STAT_IDLE;
        }
      break;

    case EV_CONNECTED: //3

        //LOCKFLAG=0;MOTORFLAG=0;
        ledIslemleri(6);//MAVİ
        PPBAK ();
        if(onayStatus==ONAY_STAT_IZIN_VERILDI){
          sarjStatus=SARJA_HAZIR;
        }
        if(cpStatus==CP_STAT_NO_EV){
          sarjStatus=SARJ_STAT_IDLE;
        }
        if(ppStatus==PP_STAT_ERROR){
        sarjStatus=SARJ_STAT_IDLE;
        }
    break;

    case SARJA_HAZIR: //4
     if(LOCKFLAG==0) {
      lock(LOCK_PULSE_MS);
      delay (50);
      LOCKFLAG=1;
      relayDriver(1);
      RelayFlag=1;
        digitalWrite(RST_PIN,LOW);
        delay(200);
        digitalWrite(RST_PIN,HIGH);
        rfid.PCD_Init();
      }
       if(cpStatus==CP_STAT_NO_EV) {
       //MOTORFLAG=0;
        sarjStatus=SARJ_STAT_FAULT_HARD;
        }

      if(cpStatus==CP_STAT_CHARGING) sarjStatus=SARJ_STAT_SARJ_BASLADI;
    break;

    case SARJ_STAT_SARJ_BASLADI: //5
      ledIslemleri(7); //YEŞİL
      if(cpStatus==CP_STAT_EV_CONNECTED){
        relayDriver(0);
        delay(10);
        //RelayFlag=0;
        LOCKFLAG=0;
        sarjStatus=SARJ_STAT_SARJ_DURAKLATILDI;
      }
      else if(onayStatus==ONAY_STAT_IPTAL_ISTENDI){
        sarjStatus=SARJ_STAT_SARJ_BITIR;
      }

      else if(cpStatus==CP_STAT_NO_EV){
        sarjStatus=SARJ_STAT_SARJ_BITIR;
         }
    break;

    case SARJ_STAT_SARJ_DURAKLATILDI: //6
     ledIslemleri(8);
      if(cpStatus==CP_STAT_CHARGING){
        sarjStatus=SARJA_HAZIR;
      }
      if(onayStatus==ONAY_STAT_IPTAL_ISTENDI){
       sarjStatus=SARJ_STAT_SARJ_BITIR;
       delay(100);
      }

     if(cpStatus==CP_STAT_NO_EV) {
      sarjStatus=SARJ_STAT_SARJ_BITIR; 
      
     }
        if(cpStatus==CP_STAT_CHARGING) sarjStatus=SARJA_HAZIR;
    break;

    case SARJ_STAT_SARJ_BITIR: //7
      {
        static unsigned long finishingStartTime = 0;

        // v4.7.0: Initialize timeout on first entry
        if (finishingStartTime == 0) {
          finishingStartTime = millis();
        }
      PWMVAL = 255;  // "Arabaya ben şarjı kesiyorum bilgisi" 6.11.25
      analogWrite(PWM_PIN, PWMVAL);
      OLDPWM = PWMVAL;
      authEnabled = false;
      delay(200); // Bu değer duruma göre uzatılabilir 6.11.25
      relayDriver(0);
      kart_flag=0;
      RelayFlag=0;
      delay(200);

      if(LOCKFLAG==0) {
        
        unlock(500);  // Increased pulse duration: 500ms → 1000ms (üretici: 500ms)  
        LOCKFLAG=1;
        delay(10);
        digitalWrite(RST_PIN,LOW);
        delay(10);
        digitalWrite(RST_PIN,HIGH);
        rfid.PCD_Init();
      }
      
      ledIslemleri(9);
      PPBAK();
        if (ppStatus == PP_STAT_ERROR) {
          SerialUSB.println("<INFO;MSG=FINISHING_EXIT_STATION_CABLE_DISCONNECTED;>");
          sarjStatus = SARJ_STAT_IDLE;
          onayStatus = ONAY_STAT_BEKLENIYOR;
          finishingStartTime = 0;  // Reset timeout
        }

        //else if (millis() - finishingStartTime > 60000) {   //BURASI BOZUYOR BİR BAKALIM
          //SerialUSB.println("<WARN;MSG=FINISHING_TIMEOUT_60S;>");
          //SerialUSB.println("<INFO;MSG=Connector should be unlocked, cable removable;>");
          //sarjStatus = SARJ_STAT_IDLE;
          //onayStatus = ONAY_STAT_BEKLENIYOR;
        //}
      }
    break;

    case SARJ_STAT_FAULT_HARD: //8
      onayStatus=ONAY_STAT_BEKLENIYOR;
      kart_flag=0;
      RelayFlag=0;
      LOCKFLAG=0;

      PWMVAL = 255;
      analogWrite(PWM_PIN, PWMVAL);
      OLDPWM = PWMVAL;
      if(MOTORFLAG==0) {
        relayDriver(0);
        delay(200);
        unlock(700);
        MOTORFLAG=1;
        LOCKFLAG=0;
        delay(10);
        digitalWrite(RST_PIN,LOW);
        delay(10);
        digitalWrite(RST_PIN,HIGH);
        rfid.PCD_Init();
      }

        if (powerBoardStat==POWER_BOARD_NO_PHASE){
          ledIslemleri(3);//FAZ HATASI
        }
        if (powerBoardStat==POWER_BOARD_NO_EARTH){
          ledIslemleri(1);
        }
        if (KabloHata==1){
          ledIslemleri(4);
          delay(5000);
          sarjStatus=SARJ_STAT_IDLE;
          MOTORFLAG=0;
        }

        if(cpStatus==CP_STAT_EV_CONNECTED){
        KabloHata=0;
       }
        if ((powerBoardStat==POWER_BOARD_NO_ERROR)&&(KabloHata==0)){
        hardFaultSay=0;
        sarjStatus=HARDFAULT_END;
          }

    break;

    case HARDFAULT_END: //0
        hardFaultSay ++;
        if (hardFaultSay>100){
        hardFaultSay=0;
        sarjStatus=SARJ_STAT_IDLE;
        }
     break;
    }
}
/**************************************************************/


//void powerBoardCom(void)
//}

bool fgbak(){

    bool p1;
    fgtest(10);
    delay(400);
    p1=digitalRead(FG_AC_PIN);
    uint starttime=millis();
    while (p1==0){
    p1=digitalRead(FG_AC_PIN);
    if ((millis()-starttime)>1200 or p1) break;
    }
      return p1;
}

bool fgcheck (uint8_t value) {

  bool error=false;

  bool fgerr;
  fgerr= (value>>0)&& 1;

  if (fgerr) error=true;

    fgerr= (value>>1)&& 1;

  if (fgerr) error=true;
  return error;
}

//***************************************************************


void usbHaberlesmeBak(void){
  uint8_t gelenVeri,i;
  //eger gelen byte varsa
  if(Serial.available()>0){
    gelenVeri=Serial.read();
    if(usbRxStatus==COM_STAT_RX_IDLE){
      if(gelenVeri==0x3C){  //"<"
        usbRxBuff[0]=gelenVeri;
        usbRxLen=1;
        usbRxStatus=COM_STAT_RX_START;
      }
    }
    else if(usbRxStatus==COM_STAT_RX_START){
      usbRxBuff[usbRxLen]=gelenVeri;
      usbRxLen++;
      if(gelenVeri==0x3E){   //">" 
        usbRxStatus=COM_STAT_RX_END;
      }
    }
  }
}

void usbVeriBak() {
  uint8_t komut = 255; 
  uint8_t val   = 0;
  const uint8_t HEADER = 0x41; // 'A'
  const uint8_t COMMA  = 0x2C; // ','

  // Header gelene kadar oku ve atla
  while (Serial.available() > 0 && Serial.peek() != HEADER) {
    Serial.read(); // yanlış byte'ı at
  }

  // Artık header ilk byte
  if (Serial.available() >= 5) {
    uint8_t header = Serial.read(); // bu kesin 'A'
    komut  = Serial.read();         // **burada local değil, fonksiyon değişkeni kullanılıyor**
    uint8_t comma  = Serial.read();
    val    = Serial.read();         // aynı şekilde fonksiyon değişkeni
    uint8_t tail   = Serial.read();

    if (comma != COMMA) {
      SerialUSB.println("<ERR;INVALID_COMMA>");
      return;
    }
  } else {
    return; // henüz 5 byte gelmediyse çık
  }

  // --- Switch-case artık doğru çalışır ---
  switch (komut) {

    case KOMUT_READ_STAT:
      sendStat();
      SerialUSB.println("<ACK;CMD=READSTAT;STATUS=OK;>");
      break;

    case KOMUT_AUTH: // 1
      if (val == 1) {
        if (sarjStatus!=SARJ_STAT_IDLE){
        authEnabled = true;
        onayStatus = ONAY_STAT_IZIN_VERILDI;
        LOCKFLAG=0; RelayFlag=0;
        stopRequested = false;
        SerialUSB.println("<ACK;CMD=AUTH;STATUS=OK;>");
        }
      } else {
        if((sarjStatus=SARJ_STAT_SARJ_DURAKLATILDI)|| (SARJ_STAT_SARJ_BASLADI)){
        authEnabled = false;
        onayStatus = ONAY_STAT_IPTAL_ISTENDI;
        LOCKFLAG=0; RelayFlag=0;
        SerialUSB.println("<ACK;CMD=AUTH;STATUS=CLEARED;>");
        } else SerialUSB.println("<ACK;CMD=AUTH;STATUS=NOT CLEARED;>"); 
      }
      break;

    case KOMUT_SET_MAX_AMP: //2
      if (sarjStatus=SARJ_STAT_IDLE){
      if (val >= 6 && val <= DEFAULT_MAX_CURRENT) {
        maxCurrent = val;
        SerialUSB.println("<ACK;CMD=SETMAXAMP;STATUS=OK;>");
      } else {
        SerialUSB.println("<ACK;CMD=SETMAXAMP;STATUS=ERR;>");
      }
    }
      break;

    case KOMUT_KILIT: {  //3 
      static uint8_t LK = 0; 
      static uint8_t ULK = 0;

      if (val == 0) {
        if (ULK == 0) {
          unlock(500);
          SerialUSB.println("<ACK;CMD=UNLOCK;STATUS=OK;>");
          ULK = 1;
          LK = 0;
        }
      } else {
        if (LK == 0) {
          lock(500);
          SerialUSB.println("<ACK;CMD=LOCK;STATUS=OK;>");
          LK = 1;
          ULK = 0;
        }
      }
      break;
    }

    case STATE_MACH:{  // 
      sarjStatus=val;
      LOCKFLAG=0; RelayFlag=0;  
    }
      break;
    default:
      SerialUSB.println("<ACK;CMD=UNKNOWN;STATUS=ERR;>");
      break;
  }
}




uint32_t ascToDec(uint8_t* veri, uint8_t index){
  uint8_t i,t;
  uint32_t vl;
  vl=0;

  for(i=1;i<10;i++){
    /*
    SerialUSB.print("Genel Veri=");
    SerialUSB.print((char*)veri);
    SerialUSB.print("index=");
    SerialUSB.println(index,DEC);
    */
    if((veri[index+i]>0x2F)&&(veri[index+i]<0x3A)){
      t=veri[index+i]-0x30;
      vl=vl*10;
      vl=vl+t;
    }
    else if(veri[index+i]==0x3B){return vl;}
    else{return 0xFFFFFFFF;}
  }
}

 //* Helper routine to dump a byte array as dec values to Serial.

void printDec(byte *buffer, byte bufferSize) {
  for (byte i = 0; i < bufferSize; i++) {
    SerialUSB.print(' ');
    SerialUSB.print(buffer[i], DEC);
  }
}

void sendStat(int id) {
  SerialUSB.print(F("<STAT;"));
  if (id >= 0) {
    SerialUSB.print(F("ID="));
    SerialUSB.print(id);
    SerialUSB.print(';');
  }
  SerialUSB.print(F("CP="));
  SerialUSB.print(cpStatus);
  SerialUSB.print(F(";CPV="));
  SerialUSB.print(cpReelVal);
  SerialUSB.print(F(";PP="));
  SerialUSB.print(ppStatus);
  SerialUSB.print(F(";PPV="));
  SerialUSB.print(ppReadVal);
  SerialUSB.print(F(";RL="));
  SerialUSB.print(RelayFlag);
  SerialUSB.print(F(";LOCK="));
  SerialUSB.print(LOCKFLAG);
  SerialUSB.print(F(";MOTOR="));
  SerialUSB.print(MOTORFLAG);
  SerialUSB.print(F(";PWM="));
  SerialUSB.print(PWMVAL);
  SerialUSB.print(F(";MAX="));
  SerialUSB.print(maxCurrent);
  SerialUSB.print(F(";CABLE="));
  SerialUSB.print(cableCurrent);
  SerialUSB.print(F(";AUTH="));
  SerialUSB.print(authEnabled ? 1 : 0);
  SerialUSB.print(F(";STATE="));
  SerialUSB.print(sarjStatus);
  SerialUSB.print(F(";PB="));
  SerialUSB.print(powerBoardStat);
  SerialUSB.print(F(";STOP="));
  SerialUSB.print(stopRequested ? 1 : 0);
  SerialUSB.println(F(";>"));
}

uint8_t readMultiplexer(uint8_t adr){
  uint8_t dat;
  digitalWrite(MULTIP_OE,HIGH);

  if((adr & 0x01)==0){digitalWrite(DLATCH_ADR0,LOW);}
  else{digitalWrite(DLATCH_ADR0,HIGH);}
  if((adr & 0x02)==0){digitalWrite(DLATCH_ADR1,LOW);}
  else{digitalWrite(DLATCH_ADR1,HIGH);}
  if((adr & 0x04)==0){digitalWrite(DLATCH_ADR2,LOW);}
  else{digitalWrite(DLATCH_ADR2,HIGH);}

  digitalWrite(MULTIP_OE,LOW);
  delay(1);
  dat=digitalRead(MULTIP_INP);
  digitalWrite(MULTIP_OE,HIGH);

  return dat;
}


/*void sendPowerCommand(uint8_t comm){
  myPort.write(0x21); //!
  myPort.write(0x52); //R
  myPort.write(comm);
}
*/
void checkMyPort() {
  // ---- Power Board: 7-byte sabit paket okuyucu ----
  // Paket biçimi (indisler): buf[0]='R', buf[1]='0'/'1'/'2', buf[2],buf[3],buf[4],buf[5] ∈ {'0','1'}, buf[6]=dolgu/rezerv
  static char pwrBuf[7];
  static uint8_t pwrIdx = 0;
  static unsigned long pwrT0 = 0;

  if (myPort.available() > 0) {
    while (myPort.available() > 0) {
      int ch = myPort.read();
      if (ch < 0) break;

      if (pwrIdx == 0) pwrT0 = millis(); // İlk byte zaman damgası
      pwrBuf[pwrIdx++] = (char)ch;

      // 7 bayt tamamlandı mı?
      if (pwrIdx == 7) {
        bool ok = true;
        char resolved = '?'; // '0' / '1' / '2'

        // Temel format kontrolü
        if (pwrBuf[0] != 'R') ok = false;
        if (pwrBuf[1] != '0' && pwrBuf[1] != '1' && pwrBuf[1] != '2') ok = false;
        if (!((pwrBuf[2] == '0' || pwrBuf[2] == '1') &&
              (pwrBuf[3] == '0' || pwrBuf[3] == '1') &&
              (pwrBuf[4] == '0' || pwrBuf[4] == '1') &&
              (pwrBuf[5] == '0' || pwrBuf[5] == '1'))) {
          ok = false;
        }

        if (ok) {
        //   // Eğer 1. karakter '1' ise
           if (pwrBuf[1] == '0') resolved = '0'; // Sorun yok
           if (pwrBuf[1] == '1') resolved = '1'; // Sadece faz hatası
           if (pwrBuf[1] == '2') resolved = '2'; // Sadece Toprak Hatası
        }
        //     // 2/3/4 hepsi 1 ise → veri hatalı
        //     if (pwrBuf[2] == '1' && pwrBuf[3] == '1' && pwrBuf[4] == '1') {
        //       resolved = '0';
        //     }
        //     // else if (pwrBuf[5] == '0') {
        //     //   // Faz hatası + toprak hatası varsa → öncelik toprakta
        //     //   resolved = '2';
        //     // } else {
        //
        //     // }
        //   }
        //   else if (pwrBuf[1] == '2') {
        //     if (pwrBuf[5] == '0') {
        //       resolved = '2'; // Toprak hatası
        //     } else {
        //       resolved = '0'; // Sorun yok
        //     }
        //   }
        //   else if (pwrBuf[1] == '0' &&
        //            pwrBuf[2] == '1' &&
        //            pwrBuf[3] == '1' &&
        //            pwrBuf[4] == '1' &&
        //            pwrBuf[5] == '1') {
        //     resolved = '0'; // Her şey düzgün
        //   }
        //   else {
        //     ok = false; // Bilinmeyen durum
        //   }
        // }

        // v4.7.0: FALSE POSITIVE FILTERING
        // Timeout reset: Reset counters if no faults for 30s
        if ((phaseFaultCounter > 0 || groundFaultCounter > 0) &&
            (millis() - lastFaultTime > FAULT_RESET_TIMEOUT_MS)) {
          SerialUSB.println("<WARN;MSG=FAULT_TIMEOUT_RESET;>");
          phaseFaultCounter = 0;
          groundFaultCounter = 0;
        }

        // Relay switching mask: Ignore faults for 2s after relay switch
        bool inRelaySwitchMask = (millis() - lastRelaySwitchTime) < FAULT_MASK_WINDOW_MS;

        // Geçerliyse durumları uygula
        if (ok) {
          if (resolved == '2') {
            // Ground fault detected
            if (inRelaySwitchMask) {
              SerialUSB.println("<WARN;MSG=GF_IGNORED_RELAY_MASK;>");
            } else {
              groundFaultCounter++;
              lastFaultTime = millis();
              SerialUSB.print("<INFO;MSG=GF_COUNT;VAL=");
              SerialUSB.print(groundFaultCounter);
              SerialUSB.println(";>");

              if (groundFaultCounter >= CONSECUTIVE_FAULT_THRESHOLD) {
                SerialUSB.println("<WARN;MSG=GF_CONFIRMED;>");
                powerBoardStat = POWER_BOARD_NO_EARTH;
                sarjStatus = SARJ_STAT_FAULT_HARD;
                groundFaultCounter = 0;  // Reset for next cycle
              }
            }
          } else if (resolved == '1') {
            // Phase fault detected
            if (inRelaySwitchMask) {
              SerialUSB.println("<WARN;MSG=PF_IGNORED_RELAY_MASK;>");
            } else {
              phaseFaultCounter++;
              lastFaultTime = millis();
              SerialUSB.print("<INFO;MSG=PF_COUNT;VAL=");
              SerialUSB.print(phaseFaultCounter);
              SerialUSB.println(";>");

              if (phaseFaultCounter >= CONSECUTIVE_FAULT_THRESHOLD) {
                SerialUSB.println("<WARN;MSG=PF_CONFIRMED;>");
                powerBoardStat = POWER_BOARD_NO_PHASE;
                sarjStatus = SARJ_STAT_FAULT_HARD;
                phaseFaultCounter = 0;  // Reset for next cycle
              }
            }
          } else { // '0'
            // Normal status - reset all counters
            if (phaseFaultCounter > 0 || groundFaultCounter > 0) {
              SerialUSB.println("<INFO;MSG=FAULT_CLEARED;>");
            }
            phaseFaultCounter = 0;
            groundFaultCounter = 0;
            powerBoardStat = POWER_BOARD_NO_ERROR;
          }
        }

        // Sonraki paket için sıfırla
        pwrIdx = 0;
        pwrT0  = 0;
      }
    }
  }

  // 50 ms içinde 7 bayt tamamlanmadıysa → giriş tamponunu temizle ve baştan bekle
  if (pwrIdx > 0 && (millis() - pwrT0) >= 50) {
    while (myPort.available() > 0) (void)myPort.read();
    pwrIdx = 0;
    pwrT0  = 0;
  }
}



  // if(myPort.available()>0){
  //   frompwr=myPort.readStringUntil('\n');
  //   SerialUSB.print("RX:");
  //   SerialUSB.println(frompwr);

  //   //powerBoardStat=POWER_BOARD_NO_ERROR;

  //   if(frompwr.substring(0,1)=="R"){

  //       if (frompwr.substring(1,2)=="1") {
  //      // SerialUSB.println("Hata");
  //       powerBoardStat=POWER_BOARD_NO_PHASE;
  //       sarjStatus=SARJ_STAT_FAULT_HARD;
  //       }

  //      if (frompwr.substring(1,2)=="2") {
  //      // SerialUSB.println("Hata");
  //       powerBoardStat=POWER_BOARD_NO_EARTH;
  //       sarjStatus=SARJ_STAT_FAULT_HARD;
  //       }

  //      if ((frompwr.substring(1,2)=="0")&&(KabloHata==0)) {
  //       powerBoardStat=POWER_BOARD_NO_ERROR;
  //       }
  //   }

  //  }




//*                           LOOP                              *
//***************************************************************
// ============================================================================
// GPIO UART COMMAND HANDLER
// ============================================================================
// #if USE_DUAL_UART
// // GPIO UART: Byte-by-byte reading (same as USB Serial)
// void gpioHaberlesmeBak(void) {
//   uint8_t gelenVeri;
//   // Read ALL available bytes in one loop cycle (prevent buffer overflow)
//   while (SerialGPIO.available() > 0) {
//     gelenVeri = SerialGPIO.read();
//     if (gpioRxStatus == COM_STAT_RX_IDLE) {
//       if (gelenVeri == 0x3C) {  // '<'
//         gpioRxBuff[0] = gelenVeri;
//         gpioRxLen = 1;
//         gpioRxStatus = COM_STAT_RX_START;
//       }
//     }
//     else if (gpioRxStatus == COM_STAT_RX_START) {
//       gpioRxBuff[gpioRxLen] = gelenVeri;
//       gpioRxLen++;
//       if (gelenVeri == 0x3E) {  // '>'
//         gpioRxStatus = COM_STAT_RX_END;
//         break;  // Message complete, exit loop
//       }
//     }
//   }
// }

// void gpioVeriBak() {
//   if (gpioRxStatus != COM_STAT_RX_END) return;
//   gpioRxStatus = COM_STAT_RX_IDLE;

//   unsigned long startTime = micros();
//   uint32_t val = 0;

//   // Remove '<' and '>' from buffer before parsing
//   // gpioRxBuff[0] = '<', gpioRxBuff[gpioRxLen-1] = '>'
//   // Pass only the command part: gpioRxBuff+1, gpioRxLen-2
//   uint8_t komut = komutBak(gpioRxBuff + 1, gpioRxLen - 2, &val);

//   switch (komut) {
//     case KOMUT_READ_STAT:
//       sendStat();
//      // SerialGPIO.println("<ACK;CMD=READSTAT;STATUS=OK;>");
//       SerialUSB.println("GPIO: READSTAT -> OK");
//       break;

//     case KOMUT_AUTH:
//       if (val != 0) {
//         authEnabled = true;
//         onayStatus = ONAY_STAT_IZIN_VERILDI;
//         stopRequested = false;
//        // SerialGPIO.println("<ACK;CMD=AUTH;STATUS=OK;>");
//         SerialUSB.println("GPIO: AUTH -> OK");
//       } else {
//         authEnabled = false;
//         onayStatus = ONAY_STAT_IPTAL_ISTENDI;
//         maxCurrent = DEFAULT_MAX_CURRENT;
//         sessionMaxCurrent = DEFAULT_MAX_CURRENT;
//         PWMVAL = 255;
//         analogWrite(PWM_PIN, PWMVAL);
//         OLDPWM = PWMVAL;
//        // SerialGPIO.println("<ACK;CMD=AUTH;STATUS=CLEARED;>");
//         SerialUSB.println("GPIO: AUTH -> CLEARED");
//       }
//       break;

//     case KOMUT_STOP:
//       stopRequested = true;
//      // SerialGPIO.println("<ACK;CMD=STOP;STATUS=OK;>");
//       SerialUSB.println("GPIO: STOP -> OK");
//       break;

//     case KOMUT_CURRENT:
//       if (val >= 6 && val <= 32) {
//         maxCurrent = val;
//         sessionMaxCurrent = val;
//        // SerialGPIO.printf("<ACK;CMD=CURRENT;VALUE=%d;STATUS=OK;>\n", val);
//         SerialUSB.printf("GPIO: CURRENT=%dA -> OK\n", val);
//       } else {
//        // SerialGPIO.println("<ACK;CMD=CURRENT;STATUS=ERR;REASON=OUT_OF_RANGE;>");
//         SerialUSB.printf("GPIO: CURRENT=%dA -> ERR (6-32A)\n", val);
//       }
//       break;

//     case KOMUT_UNLOCK:
//       // Send response BEFORE blocking delay
//       //SerialGPIO.println("<ACK;CMD=UNLOCK;STATUS=OK;>");
//       SerialUSB.println("GPIO: UNLOCK -> OK");
//       unlock(500);
//       break;

//     case KOMUT_LOCK:
//       // Send response BEFORE blocking delay
//       //SerialGPIO.println("<ACK;CMD=LOCK;STATUS=OK;>");
//       SerialUSB.println("GPIO: LOCK -> OK");
//       lock(500);
//       break;

//     default:
//       //SerialGPIO.println("<ACK;CMD=UNKNOWN;STATUS=ERR;>");
//       SerialUSB.print("GPIO: UNKNOWN (");
//       for (uint8_t i = 0; i < gpioRxLen; i++) {
//         SerialUSB.write(gpioRxBuff[i]);
//       }
//       SerialUSB.println(")");
//       break;
//   }

//   unsigned long responseTime = micros() - startTime;
//   SerialUSB.printf("GPIO Response: %lu us (%.2f ms)\n",
//                    responseTime, responseTime / 1000.0);
// }
// #endif

void loop() {
// #if USE_DUAL_UART
//   // GPIO UART: HIGH PRIORITY - Handle commands first (low latency)
//   gpioHaberlesmeBak();
//   gpioVeriBak();
// #endif

  checkMyPort();
  dutyHesapIslemleri();
  seviyeHesapla();
  CPBAK();
  kartIslemleri();
  sarjIslemleri();
  //usbHaberlesmeBak();
  usbVeriBak();

  // authEnabled = (onayStatus == ONAY_STAT_IZIN_VERILDI);
  // if (sarjStatus != prevSarjStatus) {
  //   if (sarjStatus == SARJ_STAT_IDLE) {
  //     stopRequested = false;
  //     maxCurrent = DEFAULT_MAX_CURRENT;
  //     sessionMaxCurrent = DEFAULT_MAX_CURRENT;
  //   }
  //   prevSarjStatus = sarjStatus;
  // }
  if (millis() - lastStatTime >= 7500) {
    sendStat();
    lastStatTime = millis();
  }

}
