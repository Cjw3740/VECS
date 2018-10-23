#include <dht.h>




#include <Wire.h>
#include "RTClib.h"

#include <Time.h>
#include <TimeLib.h>



RTC_DS3231 rtc;


const byte numChars = 32;
char receivedChars[numChars];

boolean newData = false;

int num_relays = 16;

float t1 = 75.5;
float h1 = 65.5;
float t2 = 75.5;
float h2 = 65.5;
int YYYY = 2018;
int MM = 10;
int DD = 11;
int hh = 10;
int mm = 22;
int ss = 45;

float TH = 80.0;
float TL = 67.0;
float HH = 99.0;
float HL = 70.0;

int MC = 0;
String CurrentORState = "NN";


String RelayState = "0000000000000000";
String last_RelayState = RelayState;

String NN = "2222222222222222";
String HN = "2222222222222222";
String CN = "2222222222222222";
String NW = "2222222222222222";
String HW = "2222222222222222";
String CW = "2222222222222222";
String ND = "2222222222222222";
String HD = "2222222222222222";
String CD = "2222222222222222";

String ORStates[9] = {NN,HN,CN,NW,HW,CW,ND,HD,CD};
int ORState_num = 0;

String ToDo[] = {"0823451000000000000000","2030110000000000000000"};





//***** Setup *****
void setup() {
    Serial.begin(9600);
    
    //Serial.println("<Arduino is ready>");



// start the rtc, and if it can't let the pi know
 if (! rtc.begin()) {
    Serial.println("Couldn't find RTC");
    while (1);
  }
//sets system time from RTC on bootup
DateTime now = rtc.now();
setTime(now.hour(), now.minute(), now.second(), now.day(), now.month(), now.year());
    
     
}





//********** MAIN LOOP **********

void loop() {
  last_RelayState = RelayState;
    //getSensorData();
    getInput();
    instruction_handle();
    determineRS_shouldbe();   //use the MC, ToDo list, and override state to determine what the relay state should be
    update_RS();     //if RS changed, shift out
    
}
//********************************



//Recieves instructions from the pi as defined by start/end brakets <>
void getInput() {
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






// Handles instructions from the Pi
void instruction_handle() {
    if (newData == true) {

      if(String(receivedChars)[0] == 'G'){
        //do get things
        if(String(receivedChars)[1] == 'A'){
          YYYY = year();
          MM = month();
          DD = day();
          hh = hour();
          mm = minute();
          ss = second();
          // format: YYYY:MM:DD:HH:mm:ss-RelayState-t1/h1:t2/h2-MC-OR
          String reply = String(YYYY)+":"+String(MM)+":"+String(DD)+":"+String(hh)+":"+String(mm)+":"+String(ss)+"-"+RelayState+"-"+String(t1)+"/"+String(h1)+":"+String(t2)+"/"+String(h2)+"-"+String(MC)+"-"+CurrentORState;
          Serial.println(reply);
    
        } else if(String(receivedChars)[1] == 'T'){
          //get the time from the rtc and set the system time to it
          DateTime now = rtc.now();
          setTime(now.hour(), now.minute(), now.second(), now.day(), now.month(), now.year());
        }

      
      } else if(String(receivedChars)[0] == 'S'){
        //do set things
        if(String(receivedChars)[1]=='T'){
          //set the date and time  format: STYYYYMMDDhhmmss
          YYYY = String(receivedChars).substring(2,6).toInt();
          MM = String(receivedChars).substring(6,8).toInt();
          DD = String(receivedChars).substring(8,10).toInt();
          hh = String(receivedChars).substring(10,12).toInt();
          mm = String(receivedChars).substring(12,14).toInt();
          ss = String(receivedChars).substring(14,16).toInt();
          
          setTime(hh, mm, ss, DD, MM, YYYY);
          rtc.adjust(DateTime(YYYY, MM, DD, hh, mm, ss));   
          
        } else if(String(receivedChars)[1] == 'O'){
          //sets the override thresholds in format:SOTH.HTL.LHH.HHL.L
          TH = String(receivedChars).substring(2,6).toFloat();
          TL = String(receivedChars).substring(6,10).toFloat();
          HH = String(receivedChars).substring(10,14).toFloat();
          HL = String(receivedChars).substring(14,18).toFloat();
          
        }else if(String(receivedChars)[1] == 'R'){
          //set the override relay states
          //send SRSTART
          //then the relay states in order
          //then SRSTOP
          
        }else if(String(receivedChars)[1] == 'P'){
          //set main Program or ToDo list
          //send SPSTART
          //Then the relay state should be list, in chronological order
          //Then SPSTOP
      }
      

      
      }else if(String(receivedChars).charAt(0) == 'M'){
        //do manual control things
        if(String(receivedChars).charAt(1)=='0'){
          MC = 0;
          Serial.println("MCOFF");
        } else if(String(receivedChars).charAt(1) == '1'){
          MC = 1;
          Serial.println("MCON");
        }else if(String(receivedChars).charAt(1) == 'R'){
          RelayState = String(receivedChars).substring(2);
          Serial.println(receivedChars);
      }

          
        }
    
    
    }
        newData = false;
}




//this checks the ToDo list, and uses the override state to figure out what the relay syate should be, then sets RelayState
void determineRS_shouldbe(){
  //is MC enabled?

    if(MC == 0){
      //RS = prog + OR in the sense that a 2 in the OR leaves the program dictated relay state unchanged, but a 1 or 0 overrights it
      for(int i=0;i<RelayState.length()-1;i++){
        if(ORStates[ORState_num][i]=='2'){
          //do not replace the corrosponding entry in relaystate
          } else {
            //need to select the appropriate OR list
            RelayState.setCharAt(i,ORStates[ORState_num][i]);
          }
      }
    }
  }




void update_RS(){
  if(RelayState != last_RelayState){
    //shift out the relay state
    }
  
  }






    
