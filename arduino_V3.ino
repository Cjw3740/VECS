
// Example 3 - Receive with start- and end-markers

const byte numChars = 32;
char receivedChars[numChars];

boolean newData = false;

int led = 13;

#include <DS3231.h>
// Init the DS3231 using the hardware interface
DS3231  rtc(SDA, SCL);


void setup() {
    Serial.begin(9600);
    //Serial.println("<Arduino is ready>");
    pinMode(led, OUTPUT);
    rtc.begin();
    
    
     // The following lines can be uncommented to set the date and time on bootup
  //rtc.setDOW(SATURDAY);     // Set Day-of-Week
  //rtc.setTime(5, 50, 0);     // Set the time, 24hr format, H,M,S
  //rtc.setDate(10, 12, 2017);   // Set the date, D, M, YYYY
  
}





//MAIN LOOP

void loop() {
    recvWithStartEndMarkers();
    instruction_handle();
          
}

void recvWithStartEndMarkers() {
    static boolean recvInProgress = false;
    static byte ndx = 0;
    char startMarker = '<';
    char endMarker = '>';
    char rc;
 
    while (Serial.available() > 0 && newData == false) {
        rc = Serial.read();

        if (recvInProgress == true) {
            if (rc != endMarker) {
                receivedChars[ndx] = rc;
                ndx++;
                if (ndx >= numChars) {
                    ndx = numChars - 1;
                }
            }
            else {
                receivedChars[ndx] = '\0'; // terminate the string
                recvInProgress = false;
                ndx = 0;
                newData = true;
            }
        }

        else if (rc == startMarker) {
            recvInProgress = true;
        }
    }
}

void instruction_handle() {
    if (newData == true) {
        
        //Serial.println(receivedChars);
        if(String(receivedChars) == "time"){
      Serial.println(rtc.getTimeStr());  
    }
        if(String(receivedChars) == "date"){
      Serial.println(rtc.getDateStr());  
    }
        if(String(receivedChars).substring(0,3) == "set"){
          if(String(receivedChars).substring(3,7) == "time"){
           //format:<settime:YYYY:MM:DD:HH:MM:SS>
           rtc.setTime((String(receivedChars).substring(19,21)).toInt(),(String(receivedChars).substring(22,24)).toInt(), (String(receivedChars).substring(25,27)).toInt());
          rtc.setDate((String(receivedChars).substring(16,18)).toInt(),(String(receivedChars).substring(13,15)).toInt(),(String(receivedChars).substring(8,12)).toInt() ); 
           //Serial.println(String("Time Set")); 
           //Serial.println(rtc.getTimeStr());
          }
        
    }
    
    
    
    
      
        newData = false;
    }
}
