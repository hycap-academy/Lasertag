#!/usr/bin/python3

CLIENT='002' #each player needs to have a different CLIENT number. Must be 3 digits and have preceding 0s.  e.g. 001, 002, 003
#LTSERVER='192.168.1.102' #insert IP address of server computer

#---------------------
#BUZZER:     GPIO5
#TRIGGER:    GPIO26
#RELOAD:     GPIO12
#IR_TX:      GPIO25
#IR_RX       GPIO18         Notes for wiring
#RED:        GPIO17
#GREEN:      GPIO27
#BLUE:       GPIO22
#I2C_SDA:    GPIO2
#I2C_SCL:    GPIO3
#---------------------

from os import _exit
from sys import exit
from time import sleep
from RPLCD.i2c import CharLCD
import time
import RPi.GPIO as GPIO
from random import randint
import ast
import lirc
import ltsounds
from subprocess import call
import threading
from datetime import datetime

GPIO.setmode(GPIO.BCM)
TRIGGER=26
RELOAD=12
RED=17
GREEN=27
BLUE=22

#  game states:
#       waiting_for_team
#       alive
#       dead

game_state='waiting_for_team'

game_wait=3

#connected=False

GPIO.setup(TRIGGER, GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(RELOAD, GPIO.IN,pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(RED, GPIO.OUT)
GPIO.setup(GREEN, GPIO.OUT)
GPIO.setup(BLUE, GPIO.OUT)



def sound(event):
    sound_thread=threading.Thread(target=sound_func,args=[event])
    sound_thread.daemon=True
    sound_thread.start()



def sound_func(event):
    #1 = LaserSound,2 = Empty Chamber (Need to reload),3 = Start Game
    #4 = Dead Tune,5 = Not used,6 = Error,7 = You got hit
    #8 = You hit them,9 = End Game,10 = Reloading, 11=Reloading2
    
    #1 = LaserSound
    #2 = Empty Chamber (Need to reload)
    #3 = Start Game
    #5 = Dead
    #6 = Error
    #7 = You got hit
    #8 = You hit them
    #9 = Game over
    #11 = Reloading
    if(event=='shoot'):
        sound_class.play(1)
    elif(event=='empty'):
        sound_class.play(2)
    elif(event=='tag_received'):
        sound_class.play(7)
    elif(event=='tag_given'):
        sound_class.play(8)
    elif(event=='error'):
        sound_class.play(6)
    elif(event=='dead'):
        sound_class.play(4)
    elif(event=='begingame'):
        sound_class.play(3)
    elif(event=='endgame'):
        sound_class.play(9)
    elif(event=='reloading'):
        sound_class.play(11)
    elif(event=='join'):
        sound_class.play(13)
    elif(event=='respawn'):
        sound_class.play(12)
    else:
        pass

def LED(color,delay):
    LED_thread=threading.Thread(target=LED_func,args=[color,delay])
    LED_thread.daemon=True
    LED_thread.start()

def LED_func(color,delay):
    GPIO.output(color,GPIO.HIGH) 
    sleep(delay)
    GPIO.output(color,GPIO.LOW) 
    
def LED_BLINK():
    LED_thread=threading.Thread(target=LED_BLINK_func,args=[])
    LED_thread.daemon=True
    LED_thread.start()

def LED_BLINK_func():
    while(True):
        if (game_state=='waiting_for_team' or game_state=='alive'):
            color=BLUE
        elif (game_state=='dead'):
            color=RED
        GPIO.output(color,GPIO.HIGH) 
        sleep(.3)
        GPIO.output(color,GPIO.LOW)
        if  (game_state=='waiting_for_team' or game_state=='dead'):
            sleep(.3)
        
    

def LED_waiting(delay):
    for color in [GREEN,BLUE,RED]:
        GPIO.output(color,GPIO.HIGH)
        sleep(delay)
        GPIO.output(color,GPIO.LOW)

def shoot(pin):
    global stats
    lcd.clear()
    lcd.home()
    if(stats['health']<=0 or stats['team']=='000'):
        if (stats['health']<=0):
            lcd.write_string("Dead\n\r")
            lcd.write_string("Can't Shoot!") 
        elif (stats['team']=='000'):
            lcd.write_string("Must Join Team!\n\r")
            lcd.write_string("Can't Shoot!") 
        sound('error')
    elif ( stats['ammo']<=0 ):
        lcd.write_string("Empty!\n\r")
        lcd.write_string("Health:" + str(stats['health']) + " Ammo:" + str(stats['ammo'])) 
        sound('empty')
    else:
        call(["irsend","SEND_ONCE","ltag",'P'+CLIENT])
        stats['shots_fired']+=1
        stats['ammo']-=1
        print("shoot: " + str(stats['ammo']))
        lcd.write_string("Shoot!\n\r")
        lcd.write_string("Health:" + str(stats['health']) + " Ammo:" + str(stats['ammo'])) 
        sound('shoot')
        LED(GREEN,0.2)
    
def tag_received(code):
    # Code looks like Playerx001 OR Basex001 Or Flagx001
    global stats, maxHealth,game_state
    print("received:" + code)
    
    from_type=code[code.find("['")+2:code.find("['")+3]
    from_number=code[code.find("['")+3:code.find("['")+6] #who was the tagger
    print ("from_type:" + from_type)
    print("from_number:" + from_number)
    if (from_type=="P" and from_number!=CLIENT and stats['health']>0 and stats['team']!='000'):
        print("Received tag from player "+ str(from_number))
        stats['health']-=1
        lcd.clear()
        lcd.home()
        lcd.write_string("Hit by:" + str(from_number) + "\n\r")
        lcd.write_string("Health:" + str(stats['health']) + " Ammo:" + str(stats['ammo'])) 
        print("Health:" + str(stats['health']))
        if(stats['health']<=0):
            game_state='dead'
            print("dead")
            lcd.clear()
            lcd.home()
            lcd.write_string("Dead\n\r")
            lcd.write_string("Respawn at base\n\r")  
            dead()
        else:
            
            sound('tag_received')
            LED(RED,0.2)
    elif (from_type=="B"):
        if(stats['team']=='000'):
            print("joined team: " + from_number)
            lcd.clear()
            lcd.home()
            lcd.write_string("Joined Team:"+ str(from_number) + "\n\r")
            lcd.write_string("Health:" + str(stats['health']) + " Ammo:" + str(stats['ammo'])) 
            stats['team']=from_number
            sound('join')
            game_state='alive'
            GPIO.output(BLUE,GPIO.HIGH) 
        else:
            if(stats['health']<=0 and stats['team']==from_number):
                game_state='alive'
                stats['health']=maxHealth
                print(str(stats['health']))
                lcd.clear()
                lcd.home()
                lcd.write_string("Respawned!\n\r")
                lcd.write_string("Health:" + str(stats['health']) + " Ammo:" + str(stats['ammo'])) 
                sound('respawn')
                LED(RED,0.2)
                LED(GREEN,0.2)
                LED(BLUE,0.2)
                GPIO.output(BLUE,GPIO.HIGH) 
        


def player_reload(pin):
    global stats,game_in_progress  #,repeat
    reload_start=time.time()
    if(stats['health']<=0 or stats['team']=='000'):
        sound('error')
    else:
        sound('reloading')
        stats['ammo'] = maxAmmo
        print("ammo" + str(stats['ammo']))
        lcd.clear()
        lcd.home()
        lcd.write_string("Reload!\n\r")
        lcd.write_string("Health:" + str(stats['health']) + " Ammo:" + str(stats['ammo'])) 

    while (GPIO.input(pin)):
        sleep(.1)
    if (time.time()-reload_start > 3.0):
        initialize('default')

def update_display():
    global stats,game_in_progress
    start_time=datetime.now()
    while game_in_progress:
        sleep(.7)
        t=datetime.now()
        td=t-start_time
        duration=" %02d:%02d "%(td.seconds//60,td.seconds%60)

def dead():
    global stats
    stats['deaths']+=1
    sound('dead')
    LED(RED,3)
    sleep(1)

def initialize(game_mode): #the game modes,Classic,Soldier,Tank,Sniper,GunGame,LaserMaster are init with
    global maxAmmo             #maxHealth,maxAmmo,maxDeaths,and waitTime(time to shoot the next shot)
    global maxHealth           #and either timed or life count number.
    global maxDeaths
    global waitTime
    global stats
    global game_wait
    global game_state

    if(game_mode=='default'):
        maxAmmo = 5
        maxHealth = 5
        stats['health'] = maxHealth
        stats['ammo'] = maxAmmo
        stats['team'] = '000'
        waitTime = 0.3
        message = "    Classic     "
        game_state='waiting_for_team'
        
    
    sleep(1)
    
    for i in range(game_wait,-1,-1):
        lcd.clear()
        lcd.home()
        lcd.write_string("    starting\n\r")
        lcd.write_string("       0"+str(i)+"       ")
        if(i==2):
            sound('begingame')
        sleep(1)
    
#----------------------------------------------------------
#                        MAIN
#----------------------------------------------------------
try:
    print("game started")
    lcd = CharLCD('PCF8574', 0x27)
    sound_class = ltsounds.Buzzer()
    sockid=lirc.init("ltag",blocking=False)
    game_in_progress=True
    GPIO.add_event_detect(TRIGGER,GPIO.RISING,shoot,bouncetime=400)
    GPIO.add_event_detect(RELOAD,GPIO.RISING,player_reload,bouncetime=400)
    
    LED_BLINK()


    while True:
        stats=dict(shots_fired=0,kills=0,deaths=0,health=0,ammo=0,team='000')


        initialize("default")
        while game_in_progress:
            sleep(.1)
            code=lirc.nextcode()
            if code:
                print(str(code))
                tag_received(str(code))
                

        sleep(5) 

finally:
    GPIO.cleanup()
