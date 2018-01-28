import pygame
from math import *  #can limit this to just the functions you need when you're closer to being done
import datetime
import json
import serial
from random import randint,triangular

pygame.init()

screen_size_x,screen_size_y  = 1600, 1000
screen = pygame.display.set_mode((screen_size_x,screen_size_y))


time_freq = 100 #freq for updating the time 1000 = 1sec
sensor_freq = 2000 #get sensor val. 1000 = 1sec

#log of serial communications
serial_comm = ["startup"]
serial_comm_max_len = 30


rawnow = datetime.datetime.now() #gets the systems version of time now
setnow = datetime.datetime(2017, 12, 2, 6, 00, 1, 1) #default time, to be overwritten by time obtained from Arduino
nowadjust = setnow - rawnow  #adjusted time


"""Relay/ToDo stuff"""
default_relay_state = "0000000000000000"
relay_state = "0000000000000000"
relay_dict = {1:"Lights",2:"Mister",3:"Fogger 1",4:"Fogger Fan 1",5:"Fogger 2",6:"Fogger Fan 2",7:"Air Circulating Fan",8:"H20 Pump",9:"unused",10:"unused",11:"unused",12:"unused",13:"unused",14:"unused",15:"unused",16:"unused"}

ToDo = []
settings_dict = {}

"""sensor related stuff"""
num_sensors = 2 #eventually number of connected sensors will dynamic
#sensor data format: time, temp1, humid1, temp2, humid2.....
#each graph will graph one sensor value (or an average)
sample_sensor_data = [[[7,0,0],75.0,82.4,76.5,83.0],[[7,0,5],76.0,81.4,76.5,84.0],[[7,0,10],75.5,80.4,76.5,85.0],[[7,0,15],74.0,79.4,76.5,82.0]]
sample_temp_data = [[[7,0,0],75.0],[[7,0,5],76.0],[[7,0,10],75.5],[[7,0,15],"Error"],[[7,0,0],"Error"],[[7,0,5],76.0],[[7,0,10],75.5],[[7,0,15],78.0],[[7,0,0],75.0],[[7,0,5],77.0],[[7,0,10],75.5],[[7,0,15],74.0]]

#this will be the big list that holds the time, sensor, relaystate,override state. To be dumped into a save file periodically to limit size
data_list = []

#max number of points to save in each small sensor reading list
max_data_points = 100
#dict for holdingt sensor data TE = example temp. Initialize with dummy value so that plot works on new startup?
data_dict = {"TE":[75.0,76.0,75.5,78.0,78.5,79.0,80.0,81.0,79.2,78.9,"Error","Error",77.1,"Error",76.8],
"T1":[],
"H1":[],
"T2":[],
"H2":[],
"T3":[],
"H3":[],
"T4":[],
"H4":[],
"TA":[],
"HA":[]}

override_dict = {"T":[80.0,70.5],"H":[100.0,70.0]}


#setting up text options (needs to be cleaned up, some use msg_obj some use font)
pygame.font.init()  #must call this
msg_obj = pygame.font.SysFont('New Times Roman', 30) #msg object to render, font and size
font = pygame.font.Font(None,30)



#defining rgb colors for easy reference
red = (255,0,0)
green = (0,255,0)
blue = (0,0,255)
white = (255,255,255)
black = (0,0,0)
light_blue = (0,255,255)
purple = (255,0,255)
yellow = (255,255,0)
orange = (255,128,0)



"""custom events to be handled by the event handler"""
CUSTOMEVENT = pygame.USEREVENT +1 #needs category attribute at a minimum
gotoscreen_MC = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'MC')
gotoscreen_Main = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Main')
gotoscreen_Debug = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Debug')
gotoscreen_Temp = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Temp')
gotoscreen_Humid = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Humid')
gotoscreen_ToDo = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'ToDo')
gotoscreen_DateTime = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'DateTime')
gotoscreen_ToDoset = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'ToDoset')
gotoscreen_ToDochange = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'ToDochange')

ToDo_change = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'edit')
ToDo_new = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'new')
ToDo_del = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'delete')
ToDo_MIS = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'MIS')

getTime = pygame.event.Event(CUSTOMEVENT, category = 'timeevent', action = 'getTime')
setTime = pygame.event.Event(CUSTOMEVENT, category = 'timeevent', action = 'setTime')


getSensorData = pygame.event.Event(CUSTOMEVENT, category = 'timeevent', action = 'getsensordata')




donothing = pygame.event.Event(CUSTOMEVENT, category = 'donothing')


UPDATE_TIME_EVENT = pygame.USEREVENT+2
SENSOR_EVENT = pygame.USEREVENT+3











"""for tracking outgoing serial communications to arduino. To be used in place of ser.write"""
def serial_send(str_data):
	global serial_comm
	serial_comm.append("Pi:" + str_data)
	ser.write(str_data.encode())
	if len(serial_comm) > serial_comm_max_len:
		del serial_comm[0]

"""for tracking incomming serial communications from arduino. To be used in place of ser.readline"""
def serial_recieve():
	global serial_comm
	recieved = ser.readline().decode('ascii')[:-1]   #the slice removes the newline
	serial_comm.append("Arduino:" + recieved[:-1])
	if len(serial_comm) > serial_comm_max_len:
		del serial_comm[0]
	return recieved


"""sets up serial com with arduino"""
def serial_comm_start():
    try:
        global ser
        ser = serial.Serial('/dev/ttyACM0', 9600,timeout=1) # Establish the connection on a specific port, must know the name of the arduino port
        serial_comm.append("serial comm sucessfull")
    except:
        serial_comm.append("serial comm failed")


def get_str_now():
	tempnow = nowadjust + datetime.datetime.now()
	return tempnow.strftime("%m/%d/%y  %H:%M:%S")

def get_str_time_now():
	tempnow = nowadjust + datetime.datetime.now()
	return tempnow.strftime("%H:%M:%S")

def get_str_date_now():
	tempnow = nowadjust + datetime.datetime.now()
	return tempnow.strftime("%m/%d/%y")



def rot_center(image,angle):
	orig_rect = image.get_rect()
	rot_image = pygame.transform.rotate(image,angle)
	rot_rect = orig_rect.copy()
	rot_rect.center = rot_image.get_rect().center
	rot_image = rot_image.subsurface(rot_rect).copy()
	return rot_image


#to take the string version of relay state and change individual "bits"
def makebit(full,bit,val):
	return full[:bit] + str(val) + full[bit+1:]

#bubble sorts ToDo list by time and removes duplicate entries (needs cleaning up and testing)
def sortlist(list1):
	for j in range(len(list1)):
		
		for i in range(len(list1)):
			if i == len(list1)-1:
				pass
			else:
				if list1[i][0] > list1[i+1][0]:
					tmp = list1[i+1]
					list1[i+1] = list1[i]
					list1[i] = tmp
				elif list1 [i][0] < list1[i+1][0]:
					pass
				else:
					if list1[i][1] > list1[i+1][1]:
						tmp = list1[i+1]
						list1[i+1] = list1[i]
						list1[i] = tmp
					elif list1 [i][1] < list1[i+1][1]:
						pass
					else:
						if list1[i][2] > list1[i+1][2]:
							tmp = list1[i+1]
							list1[i+1] = list1[i]
							list1[i] = tmp
						elif list1[i][2] < list1[i+1][2]:
							pass
						else:
							pass
	for k in range(len(list1)-1):
		if list1[k] == list1[k+1]:
			del(list1[k])
	return list1

#assumes now is a list of h,m,s. Figures out whatthe current relay state should be
def should_be_relay_state(def_state,todolist,now):
	rel_state = def_state
	for task in todolist:
		if task[0] > now[0]:
			break
		elif task[0] < now[0]:
			rel_state = makebit(rel_state,task[3],task[4])
		else:
			if task[1] > now[1]:
				break
			elif task[1] < now[1]:
				rel_state = makebit(rel_state,task[3],task[4])
			else:
				if task[0] > now[0]:
					break
				elif task[0] < now[0]:
					rel_state = makebit(rel_state,task[3],task[4])
				else:
					rel_state = makebit(rel_state,task[3],task[4])
	return rel_state

#keep replacing target with task at hand if it's past it's time - working
def last_task(todo_list,now):
	target_task = []
	for task in todo_list:
		if task[0] < now[0]:
			target_task = task
		elif task[0] > now[0]:
			break
		else:
			if task[1] < now[1]:
				target_task = task
			elif task[1] > now[1]:
				break
			else:
				if task[2] < now[2]:
					target_task = task
	return target_task

#returns first instance that satisfied a series of tiered later than statements
def next_task(todo_list,now):
	for task in todo_list:
		if task[0] > now[0]:
			return task
		elif task[0] < now[0]:
			pass
		else:
			if task[1] > now[1]:
				return task
			elif task[1] > now[1]:
				pass
			else:
				if task[2] > now[2]:
					return task
	return target_task
	

def save_settings():
	global settings_dict
	with open('SAVE.txt','w') as outfile:
		json.dump(settings_dict, outfile)
		outfile.close

#need to add backup settings to use if no save fileis found
def load_settings():
	global settings_dict
	with open('SAVE.txt','r') as infile:
		settings_dict = json.load(infile)
		infile.close

load_settings()




#to take the string version of relay state and change individual "bits"
def makebit(full,bit,val):
	return full[:bit] + val + full[bit+1:]


"""found the following function online. Don't remember where"""
def inside_polygon(x,y,points):
    """return True if (x,y) is inside polygon defined by points"""
    n = len(points)
    inside = False
    p1x,p1y = points[0]
    for i in range(1,n+1):
        p2x,p2y = points[i % n]
        if y > min(p1y,p2y):
            if y <= max(p1y,p2y):
                if x <= max(p1x,p2x):
                    if p1y != p2y:
                        xinters = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xinters:
                        inside = not inside
        p1x, p1y = p2x,p2y
    return inside



"""Objects to be used in screens. Often pushing custom defined events into the event queue"""

class control():
    def __init__(self,box): 
        self.x1,self.y1,self.x2,self.y2 = box
        self.dx = self.x2 - self.x1
        self.dy = self.y2 - self.y1
        self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))


#hexagonal toggle button - working
class button_hex_tog():
    def __init__(self,start_pos,side_len,color,text,default_state,do_pressed,do_unpressed):
        self.start_pos = start_pos
        self.x1 = start_pos[0]
        self.y1 = start_pos[1]
        self.side_len = side_len
        self.color = color
        self.text = text
        self.pressed = default_state
        self.do_pressed = do_pressed
        self.do_unpressed = do_unpressed
        self.hx = int((self.side_len * sqrt(3))/2)
        self.hy = int(self.side_len/2)
        self.center = (self.x1+self.hx,self.y1+self.hy)
        self.points = ((self.x1,self.y1),(self.x1+self.hx,self.y1-self.hy),(self.x1+(2*self.hx),self.y1),(self.x1+(2*self.hx),self.y1+(2*self.hy)),(self.x1+self.hx,self.y1+(3*self.hy)),(self.x1,self.y1+(2*self.hy)))
        self.inner_space = 5
        self.lx = self.inner_space*cos(pi/6)
        self.ly = self.inner_space*sin(pi/6)
        self.points_inner = ((self.points[0][0]+self.lx,self.points[0][1]+self.ly),(self.points[1][0],self.points[1][1]+self.inner_space),(self.points[2][0]-self.lx,self.points[2][1]+self.ly),(self.points[3][0]-self.lx,self.points[3][1]-self.ly),(self.points[4][0],self.points[4][1]-self.inner_space),(self.points[5][0]+self.lx,self.points[5][1]-self.ly))
        self.button_text_size = font.size(self.text)
        self.button_txt_loc = (self.center[0]-self.button_text_size[0]/2,self.center[1]-self.button_text_size[1]/2) #sets up text options for button label

        
    def draw(self):
        pygame.draw.polygon(screen,self.color,self.points,1) # draws outer hex
        if self.pressed:
            pygame.draw.polygon(screen,self.color,self.points_inner,0)
            button_txt = msg_obj.render(self.text,True, black, self.color)
        
        else:
            pygame.draw.polygon(screen,black,self.points_inner,0)
            button_txt = msg_obj.render(self.text,True, self.color, black)
        
        screen.blit(button_txt,self.button_txt_loc)
    
    def do(self,event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.pressed = not self.pressed
            self.draw() 
            if self.pressed:
                pygame.event.post(self.do_pressed)
            else:
                pygame.event.post(self.do_unpressed)


#hexagonal do button - working
class button_hex_do():
    def __init__(self,start_pos,side_len,color,text,default_state,do_pressed):
        self.start_pos = start_pos
        self.x1 = start_pos[0]
        self.y1 = start_pos[1]
        self.side_len = side_len
        self.color = color
        self.text = text
        self.pressed = default_state
        self.do_pressed = do_pressed
        self.hx = int((self.side_len * sqrt(3))/2)
        self.hy = int(self.side_len/2)
        self.center = (self.x1+self.hx,self.y1+self.hy)
        self.points = ((self.x1,self.y1),(self.x1+self.hx,self.y1-self.hy),(self.x1+(2*self.hx),self.y1),(self.x1+(2*self.hx),self.y1+(2*self.hy)),(self.x1+self.hx,self.y1+(3*self.hy)),(self.x1,self.y1+(2*self.hy)))
        self.inner_space = 5
        self.lx = self.inner_space*cos(pi/6)
        self.ly = self.inner_space*sin(pi/6)
        self.points_inner = ((self.points[0][0]+self.lx,self.points[0][1]+self.ly),(self.points[1][0],self.points[1][1]+self.inner_space),(self.points[2][0]-self.lx,self.points[2][1]+self.ly),(self.points[3][0]-self.lx,self.points[3][1]-self.ly),(self.points[4][0],self.points[4][1]-self.inner_space),(self.points[5][0]+self.lx,self.points[5][1]-self.ly))
        self.button_text_size = font.size(self.text)
        self.button_txt_loc = (self.center[0]-self.button_text_size[0]/2,self.center[1]-self.button_text_size[1]/2) #sets up text options for button label

        
    def draw(self):
        pygame.draw.polygon(screen,self.color,self.points,1) # draws outer hex
        if self.pressed:
            pygame.draw.polygon(screen,self.color,self.points_inner,0)
            button_txt = msg_obj.render(self.text,True, black, self.color)
        
        else:
            pygame.draw.polygon(screen,black,self.points_inner,0)
            button_txt = msg_obj.render(self.text,True, self.color, black)
        
        screen.blit(button_txt,self.button_txt_loc)
    
    def do(self,event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pygame.event.post(self.do_pressed)


#eliptical toggle button - needs testing
class button_ellipse_tog():
    def __init__(self,loc,size,color,text,default_state,do_pressed,do_unpressed):
        self.loc = loc
        self.dx,self.dy = size
        self.do_pressed = do_pressed
        self.do_unpressed = do_unpressed
        self.x1 = loc[0]
        self.y1 = loc[1]
        self.x2 = self.x1 + size[0]
        self.y2 = self.y1 +size[1]
        self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
        self.color = color
        self.pressed = default_state
        self.text = text

    def draw(self):
        
        if self.pressed:
            self.boarder = 0
            self.text_bgcolor = self.color
        else:
            self.boarder = 1
            self.text_bgcolor = black
            
        self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
        txt = msg_obj.render(self.text,True, white, self.text_bgcolor)
        pygame.draw.ellipse(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
        pygame.draw.ellipse(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),self.boarder)
        screen.blit(txt,self.txt_loc)
    
    def do(self,event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.pressed = not self.pressed
            self.draw()
            if self.pressed:
                pygame.event.post(self.do_pressed)
            else:
                pygame.event.post(self.do_unpressed)            


#eliptical do button - needs testing
class button_ellipse_do():
    def __init__(self,loc,size,color,text,default_state,do_pressed):
        self.loc = loc
        self.dx,self.dy = size
        self.do_pressed = do_pressed
        self.x1 = loc[0]
        self.y1 = loc[1]
        self.x2 = self.x1 + size[0]
        self.y2 = self.y1 +size[1]
        self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
        self.color = color
        self.pressed = default_state
        self.text = text

    def draw(self):
        
        if self.pressed:
            self.boarder = 0
            self.text_bgcolor = self.color
        else:
            self.boarder = 1
            self.text_bgcolor = black
            
        self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
        txt = msg_obj.render(self.text,True, white, self.text_bgcolor)
        pygame.draw.ellipse(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
        pygame.draw.ellipse(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),self.boarder)
        screen.blit(txt,self.txt_loc)
    
    def do(self,event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pygame.event.post(self.do_pressed)


#rectangular toggle button - needs testing
class button_rec_tog():
    def __init__(self,loc,size,color,text,default_state,do_pressed,do_unpressed):
        self.loc = loc
        self.do_pressed = do_pressed
        self.do_unpressed = do_unpressed
        self.dx,self.dy = size
        self.x1 = loc[0]
        self.y1 = loc[1]
        self.x2 = self.x1 + size[0]
        self.y2 = self.y1 +size[1]
        self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
        self.color = color
        self.pressed = default_state
        self.text = text

    def draw(self):
        
        if self.pressed:
            self.boarder = 0
            self.text_bgcolor = self.color
            txt = msg_obj.render(self.text,True, black, self.text_bgcolor)
        else:
            self.boarder = 1
            self.text_bgcolor = black
            txt = msg_obj.render(self.text,True, self.color, self.text_bgcolor)
            
        self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
        
        pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
        pygame.draw.rect(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),self.boarder)
        screen.blit(txt,self.txt_loc)
    
    def do(self,event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.pressed = not self.pressed
            self.draw()
            if self.pressed:
                pygame.event.post(self.do_pressed)
            else:
                pygame.event.post(self.do_unpressed)            


#simple button, push it, it does something - working
class button_rec_do():
    def __init__(self,loc,size,color,text,default_state,do_on_press):
        self.do_on_press = do_on_press
        self.loc = loc
        self.dx,self.dy = size
        self.x1 = loc[0]
        self.y1 = loc[1]
        self.x2 = self.x1 + size[0]
        self.y2 = self.y1 +size[1]
        self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
        self.color = color
        self.pressed = default_state
        self.text = text

    def draw(self):
        #Being pressed or unpressed is just for appearance. clicking the button does not automatically toggle the state
        if self.pressed:
            self.boarder = 0
            self.text_bgcolor = self.color
            txt = msg_obj.render(self.text,True, black, self.text_bgcolor)
        else:
            self.boarder = 1
            self.text_bgcolor = black
            txt = msg_obj.render(self.text,True, self.color, self.text_bgcolor)
            
        self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
        
        pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
        pygame.draw.rect(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),self.boarder)
        screen.blit(txt,self.txt_loc)
    
    def do(self,event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            pygame.event.post(self.do_on_press)


class button_img_do():
	def __init__(self,loc,img,do_on_press):
		self.do_on_press = do_on_press
		self.loc = self.x1,self.y1 = loc
		self.img = img
		self.image = pygame.image.load(self.img)
		self.dx,self.dy = self.image.get_size()
		self.x2,self.y2 = ((self.x1+self.dx),(self.y1+self.dy))
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		
	def draw(self):
		screen.blit(self.image,self.loc)
		
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			pygame.event.post(self.do_on_press)


class round_slider_int(control):
    def __init__(self, pos, bradius,sradius,color,min_val,max_val,initial_val):
        self.x1,self.y1 = pos
        text_size = font.size(str(initial_val)) #getting the size of the output
        self.x2,self.y2 = (self.x1+2*(bradius+sradius),self.y1+2*(bradius+sradius)+int((1.5)*text_size[1]))
        self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
        self.dx = self.x2 - self.x1
        self.dy = self.y2 - self.y1
        self.min_val = min_val
        self.max_val = max_val
        self.initial_val = initial_val
        self.val_range = max_val - min_val
        self.center = (self.x1+int(self.dx/2),self.y1+int(self.dy/2))
        self.bradius = bradius
        self.sradius = sradius
        self.color = color
        self.xp = int(round(self.bradius * cos(2*pi*(self.initial_val-self.min_val)/self.val_range - (pi/2))+self.center[0])+1) #x-coord of the initial value. The +1 ensures it is at min and not max, which technically are very close
        self.yp = int(round(self.bradius * sin(2*pi*(self.initial_val-self.min_val)/self.val_range- (pi/2)) + self.center[1])) #y-coord of the initial value
        self.dial_output = str(initial_val)
        
        
    
    def draw(self):
        axp = self.xp - self.center[0] #gets x pos relative to center
        ayp = self.yp - self.center[1] #gets y pos relative to center
        
        rx = int(self.bradius * sin(asin(axp/(sqrt(axp**2 + ayp**2)))) + self.center[0]) #gets x pos adjusted to be on big circle
        ry = int(self.bradius * cos(acos(ayp/(sqrt(axp**2 + ayp**2)))) + self.center[1]) #gets y pos adjusted to be on big circle
        
        self.dial_output = str(round(((atan2(-axp,ayp)+pi)/(2*pi))*self.val_range + self.min_val))
        text_size = font.size(self.dial_output)
        dial_out_loc = (self.center[0]-text_size[0]/2,self.y1-text_size[1])
        dial_out_txt = msg_obj.render(self.dial_output,True, white, black)
        
        pygame.draw.rect(screen,black,pygame.Rect((self.x1,self.y1-text_size[1],self.dx,self.dy+text_size[1])),0) #blacks out box
        pygame.draw.circle(screen,self.color, self.center,self.bradius,1) #draws big circle
        pygame.draw.circle(screen,self.color, self.center,self.sradius,1) #draws little center circle
        pygame.draw.circle(screen,self.color, (self.center[0],self.center[1]-self.bradius),self.sradius,1) #draws little circle at zero position
        pygame.draw.line(screen,self.color,self.center,(self.center[0],self.center[1]-self.bradius),1) #draws line up to zero position
        
        
        pygame.draw.line(screen,self.color,self.center,(rx,ry),1) #draws line to big circle
        pygame.draw.circle(screen,self.color, (rx,ry),self.sradius,1) #draws small cirlce around adjusted point on big circle
        
        
        screen.blit(dial_out_txt,dial_out_loc)
            
    def do(self,event):
        mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0] and inside_polygon(mouse_pos_x, mouse_pos_y,self.points):
            self.xp= pygame.mouse.get_pos()[0] #gets x pos of mouse
            self.yp= pygame.mouse.get_pos()[1] #gets y pos of mouse
            self.draw()


class round_slider_float(control):
    def __init__(self, pos, bradius,sradius,color,min_val,max_val,initial_val,round_to):
        self.x1,self.y1 = pos
        self.round_to = round_to
        text_size = font.size(str(initial_val)) #getting the size of the output
        self.x2,self.y2 = (self.x1+2*(bradius+sradius),self.y1+2*(bradius+sradius)+int((1.5)*text_size[1]))
        self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
        self.dx = self.x2 - self.x1
        self.dy = self.y2 - self.y1
        self.min_val = min_val
        self.max_val = max_val
        self.initial_val = initial_val
        self.val_range = max_val - min_val
        self.center = (self.x1+int(self.dx/2),self.y1+int(self.dy/2))
        self.bradius = bradius
        self.sradius = sradius
        self.color = color
        self.xp = int(round(self.bradius * cos(2*pi*(self.initial_val-self.min_val)/self.val_range - (pi/2))+self.center[0])) #x-coord of the initial value
        self.yp = int(round(self.bradius * sin(2*pi*(self.initial_val-self.min_val)/self.val_range- (pi/2)) + self.center[1])) #y-coord of the initial value
        
        
    
    def draw(self):
        axp = self.xp - self.center[0] #gets x pos relative to center
        ayp = self.yp - self.center[1] #gets y pos relative to center
        
        rx = int(self.bradius * sin(asin(axp/(sqrt(axp**2 + ayp**2)))) + self.center[0]) #gets x pos adjusted to be on big circle
        ry = int(self.bradius * cos(acos(ayp/(sqrt(axp**2 + ayp**2)))) + self.center[1]) #gets y pos adjusted to be on big circle
        
        dial_output = str(round(((atan2(-axp,ayp)+pi)/(2*pi))*self.val_range + self.min_val,self.round_to))
        text_size = font.size(dial_output)
        dial_out_loc = (self.center[0]-text_size[0]/2,self.y1-text_size[1])
        dial_out_txt = msg_obj.render(dial_output,True, white, black)
        
        pygame.draw.rect(screen,black,pygame.Rect((self.x1,self.y1-text_size[1],self.dx,self.dy+text_size[1])),0) #blacks out box
        pygame.draw.circle(screen,self.color, self.center,self.bradius,1) #draws big circle
        pygame.draw.circle(screen,self.color, self.center,self.sradius,1) #draws little center circle
        pygame.draw.circle(screen,self.color, (self.center[0],self.center[1]-self.bradius),self.sradius,1) #draws little circle at zero position
        pygame.draw.line(screen,self.color,self.center,(self.center[0],self.center[1]-self.bradius),1) #draws line up to zero position
        
        
        pygame.draw.line(screen,self.color,self.center,(rx,ry),1) #draws line to big circle
        pygame.draw.circle(screen,self.color, (rx,ry),self.sradius,1) #draws small cirlce around adjusted point on big circle
        
        
        screen.blit(dial_out_txt,dial_out_loc)
            
    def do(self,event):
        mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
        if pygame.mouse.get_pressed()[0] and inside_polygon(mouse_pos_x, mouse_pos_y,self.points):
            self.xp= pygame.mouse.get_pos()[0] #gets x pos of mouse
            self.yp= pygame.mouse.get_pos()[1] #gets y pos of mouse
            self.draw()


#keypad control using toggle buttons
class hex_pad():
	
	"""
#an example
button_list = 
[[["label",default_state,do_pressed,do_unpressed],["label2",def_st,do_p,do_up]],
[["label3",def_st,do_p,do_up],["label4",def_st,do_p,do_up],["label5",def_st,do_p,do_up]],
[["label6",def_st,do_p,do_up],["label7",def_st,do_p,do_up]]]

bl[row][col][item]
"""
	def __init__(self,initial_point,side_len,button_list,color):
		self.xo,self.yo = initial_point
		self.side_len = side_len
		self.buttons_list = button_list
		self.rows = int(len(button_list))
		self.cols_list = [int(len(button_list[i])) for i in range(self.rows)]
		self.color = color
		self.hx = int(self.side_len * (sqrt(3))/2)
		self.hy = int(self.side_len/2)
		self.points = ((self.xo-int(1.5*self.hx),self.yo-self.hy),(self.xo+4*max(self.cols_list)*self.hx,self.yo-self.hy),(self.xo+2*max(self.cols_list)*self.hx,self.yo+5*self.hy*self.rows),(self.xo-self.hx,self.yo+5*self.hy*self.rows))
		self.buttons = []
		
		for j in range(self.rows):
			for i in range(len(self.buttons_list[j])):
				self.buttons.append(button_hex_tog((self.xo+int(2.2*i*self.hx)-int(1.12*(j%2)*self.hx),self.yo+int(3.3*j*self.hy)),self.side_len,self.color,self.buttons_list[j][i][0],self.buttons_list[j][i][1],self.buttons_list[j][i][2],self.buttons_list[j][i][3]))
		
		
	def draw(self):
		for key in self.buttons:
			key.draw()
	
	def do(self,event):
		mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
		for btn in self.buttons:
			if inside_polygon(mouse_pos_x, mouse_pos_y,btn.points):
				btn.do(event) 


class time_label():
	def __init__(self,loc,size,color):
		self.loc = loc
		self.size = size
		self.color = color
		self.dx,self.dy = size
		self.x1 = loc[0]
		self.y1 = loc[1]
		self.x2 = self.x1 + size[0]
		self.y2 = self.y1 +size[1]
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		

	def draw(self):
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		self.text = get_str_time_now()
		self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
		txt = msg_obj.render(self.text,True, self.color, black)
		
		screen.blit(txt,self.txt_loc)
		
	def do(self,event):
		if event.type == UPDATE_TIME_EVENT:
			self.draw()


"""example button list: 
b_list = [[[1,"1"],[2'"2"][3,"Three"]],
[[4,"4],[5,"5"]],
[[6,"6"]]]
number to output then label
"""
class ellipse_toggle_pad():
	def __init__(self,loc,size,seperation,button_list,color,initialy_selected):
		self.loc = self.x1,self.y1 = loc
		self.size = size
		self.color = color
		self.s = seperation
		self.b_list = button_list
		self.rows = int(len(button_list))
		self.cols_list = [int(len(button_list[i])) for i in range(self.rows)]
		self.x2 = self.x1+2*(self.size[0]/2+self.s)*max(self.cols_list)
		self.y2 = self.y1+2*(self.size[1]/2+self.s)*self.rows
		self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
		self.buttons = []
		#self.output = "none"
		self.selected = initialy_selected
		for j in range(self.rows):
			for i in range(len(self.b_list[j])): 
				if self.b_list[j][i][0]== self.selected:
					istate = True
				else:
					istate = False
				self.buttons.append(button_ellipse_do((self.x1+int(i*2*(self.size[0]/2+self.s)),self.y1+j*2*(self.size[1]/2+self.s)),self.size,self.color,self.b_list[j][i][1],istate,donothing))
				
					
		
	def draw(self):
		for b in self.buttons:
			b.draw()
			
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
			for btn in self.buttons:
				if inside_polygon(mouse_pos_x, mouse_pos_y,btn.points):
					for button in self.buttons:
						if button == btn:
							button.pressed = True
							self.selected = self.buttons.index(button)+1
						else:
							button.pressed = False
						
			self.draw()



class date_label():
	def __init__(self,loc,size,color):
		self.loc = loc
		self.size = size
		self.color = color
		self.dx,self.dy = size
		self.x1 = loc[0]
		self.y1 = loc[1]
		self.x2 = self.x1 + size[0]
		self.y2 = self.y1 +size[1]
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x1,self.y2),(self.x2,self.y2))
		

	def draw(self):
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		self.text = get_str_date_now()
		self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
		txt = msg_obj.render(self.text,True, self.color, black)
		
		screen.blit(txt,self.txt_loc)
		
	def do(self,event):
		if event.type == UPDATE_TIME_EVENT:
			self.draw()

#need tomake img dependant on status and add nonrotating word in middle
class rot_image_button():
	def __init__(self,loc,img,rot_rate,do_on_press):
		self.loc = loc
		self.img = img
		self.rot_rate = rot_rate
		self.image = pygame.image.load(self.img)
		self.image = pygame.transform.scale(self.image,(200,200))
		self.base_image = self.image
		self.do_on_press = do_on_press
		self.x1,self.y1 = loc
		self.dx,self.dy = self.image.get_size()
		self.x2,self.y2 = ((self.x1+self.dx),(self.y1+self.dy))
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		self.rot_counter = 0
		
	def draw(self):
		screen.blit(self.image,self.loc)
		
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			pygame.event.post(self.do_on_press)
		
		if event.type == UPDATE_TIME_EVENT:
			if self.rot_counter < 100:
				self.image = rot_center(self.base_image,((360)*(self.rot_counter/100)))
				self.rot_counter = self.rot_counter + self.rot_rate
				self.draw()
			else:
				self.rot_counter = 0
				self.image = rot_center(self.base_image,((360)*(self.rot_counter/100)))
				self.rot_counter = self.rot_counter + self.rot_rate
				self.draw() 


class text_label():
	def __init__(self,pos,size,text,color):
		self.x1,self.y1 = pos
		self.dx,self.dy = size
		self.x2 = self.x1 + self.dx
		self.y2 = self.y1 + self.dy
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		self.text = text
		self.color = color
	
	def draw(self):
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
		txt = msg_obj.render(self.text,True, self.color, black)
		screen.blit(txt,self.txt_loc)
		
	def do(self,event):
		pass


#graphing util - in progress
#x tics define how many points to graph
class time_graph():
	global sample_temp_data
	def __init__(self,position,size,min_val,max_val,t_range,x_tics,color,title,target):
		self.x1,self.y1 = position
		self.x2, self.y2 = position[0]+size[0],position[1]+size[1]
		self.dx,self.dy = size
		self.min_val = min_val
		self.max_val = max_val
		self.t_range = t_range
		self.data = []
		self.x_tics = x_tics
		self.color = color
		self.m = (self.y2-self.y1)/(min_val-max_val)
		self.b = self.y2 - (self.y2-self.y1)/(1-(max_val/min_val))
		self.title = title
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		self.dt = round(self.dx/(x_tics-1))
		self.target = target
		
		self.h_ov = override_dict[target[0]][0]
		self.l_ov = override_dict[target[0]][1]
		
			
		
	#function for mapping a value into y-coord, bound within the max and min of the graph
	def mv(self,val):
		if isinstance(val,str): #if val is an error, just put it in the middle of the screen
			return int((self.y2-self.y1)/2 +self.y1)
		else:
			return int(max(min(val*self.m+self.b,self.y2-1),self.y1+1))
		
		
	def plot(self):
		
		pygame.draw.rect(screen,black, pygame.Rect((self.x1+1,self.y1+1,self.dx-2,self.dy-2)),0) #blacks out graph area
		pygame.draw.rect(screen,black, pygame.Rect((self.x2+1,self.y1-16,80,self.dy+32)),0) #blacks out area to right of graph
		
		#draws y axis tick marks
		for i in range(round(self.min_val),round(self.max_val),1):
			if i % 5 == 0:
				q = 5
			else:
				q = 0
			pygame.draw.line(screen,white,(self.x2,self.mv(i)),(self.x2+3+q,self.mv(i)),1)
		
		#draw high override
		pygame.draw.line(screen,red,(self.x1+1,self.mv(self.h_ov)),(self.x2-2,self.mv(self.h_ov)),1)
		#draw high override
		pygame.draw.line(screen,blue,(self.x1+1,self.mv(self.l_ov)),(self.x2-2,self.mv(self.l_ov)),1)
		
		if len(self.data)>1:
			
			#GRAPHS THE DATA
			for i in range(min(self.x_tics,len(self.data))-1):
				
				if isinstance(self.data[i+1],str):
					pygame.draw.circle(screen,yellow,(self.x2-(i+1)*self.dt-2,self.mv(self.data[i+1])),5,1)
				
				pygame.draw.line(screen,self.color,(self.x2-i*self.dt-2,self.mv(self.data[i])),(self.x2-(i+1)*self.dt-1,self.mv(self.data[i+1])),1)
		#high override
		pygame.draw.polygon(screen, red, ((self.x2+2,self.mv(self.h_ov)),(self.x2+17,self.mv(self.h_ov)-15),(self.x2+17,self.mv(self.h_ov)+15)),1)
		pygame.draw.polygon(screen, red, ((self.x2+20,self.mv(self.h_ov)-15),(self.x2+20,self.mv(self.h_ov)+15),(self.x2+70,self.mv(self.h_ov)+15),(self.x2+70,self.mv(self.h_ov)-15)),1)
		data_txt = msg_obj.render(str(self.h_ov),False, red, black)
		txt_loc =  (self.x2+27,self.mv(self.h_ov)-11)
		screen.blit(data_txt,txt_loc)
		#low override
		pygame.draw.polygon(screen, blue, ((self.x2+2,self.mv(self.l_ov)),(self.x2+17,self.mv(self.l_ov)-15),(self.x2+17,self.mv(self.l_ov)+15)),1)
		pygame.draw.polygon(screen, blue, ((self.x2+20,self.mv(self.l_ov)-15),(self.x2+20,self.mv(self.l_ov)+15),(self.x2+70,self.mv(self.l_ov)+15),(self.x2+70,self.mv(self.l_ov)-15)),1)
		data_txt = msg_obj.render(str(self.l_ov),False, blue, black)
		txt_loc =  (self.x2+27,self.mv(self.l_ov)-11)
		screen.blit(data_txt,txt_loc)
		
		
		if len(self.data)>=1: #draws the most current reading
			pygame.draw.polygon(screen, white, ((self.x2+2,self.mv(self.data[0])),(self.x2+17,self.mv(self.data[0])-15),(self.x2+17,self.mv(self.data[0])+15)),1)
			pygame.draw.polygon(screen, white, ((self.x2+20,self.mv(self.data[0])-15),(self.x2+20,self.mv(self.data[0])+15),(self.x2+70,self.mv(self.data[0])+15),(self.x2+70,self.mv(self.data[0])-15)),1)
			if self.data[0] >= self.h_ov:
				txt_col = red
			elif self.data[0] <= self.l_ov:
				txt_col = blue
			else:
				txt_col = white
			data_txt = msg_obj.render(str(self.data[0]),False, txt_col, black)
			txt_loc =  (self.x2+27,self.mv(self.data[0])-11)
			screen.blit(data_txt,txt_loc)
			
			
	def draw(self):
		#draw the box, axis labels, and title on screen change,let plot handle updating the contentsof the graph and the current value marker
		pygame.draw.rect(screen,white, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		#draws tics
		for i in range(self.x_tics+1):
			if i%10 == 0:
				q = 4
			else:
				q = 0
			pygame.draw.line(screen,white,(max(self.x2-i*(self.dt)-1,self.x1),self.y2),(max(self.x2-i*(self.dt)-1,self.x1),self.y2+3+q),1)
		
		self.plot()

		
	def do(self,event):
		if event.type == SENSOR_EVENT:
			global data_dict
			self.data = data_dict[self.target]
			self.plot()


class debug_window():
	def __init__(self,pos,ser_com):
		self.x1,self.y1 = pos
		self.data = ser_com
		self.x2,self.y2 = (self.x1+400,self.y1+((serial_comm_max_len+1)*font.size("Example")[1]))
		self.dx = self.x2-self.x1
		self.dy = self.y2-self.y1
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
	
	def draw(self):
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,light_blue, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		count = 0
		for entry in self.data:
			if entry[0] == "P":
				col = green
			elif entry[0] == "A":
				col = red
			else:
				col = white
				
			txt = msg_obj.render(entry,True, col,black)
			screen.blit(txt,(self.x1+5,self.y1+(count*font.size("Example")[1])+5))
			count = count + 1
		
	def do(self,event):
		if event.type == UPDATE_TIME_EVENT:
			self.draw()


class ToDo_window():
	def __init__(self,pos,todo_lst):
		self.x1,self.y1 = pos
		self.data = todo_lst
		self.x2,self.y2 = (self.x1+500,self.y1+((serial_comm_max_len+1)*font.size("Example")[1]))
		self.dx = self.x2-self.x1
		self.dy = self.y2-self.y1
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		self.entry_hight = font.size("Example")[1]
		self.selected = "none"
		
	def draw(self):
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,light_blue, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		count = 0
		
		for entry in self.data:
			if entry[4]:
				rs = "ON"
			else:
				rs = "OFF"
			
			hms = []
			for element in entry:
				if len(str(element)) < 2:
					hms.append("0"+str(element))
				else:
					hms.append(str(element))
			
			text_entry = hms[0]+":"+hms[1]+":"+hms[2]+"  "+relay_dict[entry[3]]+"  "+rs
			txt = msg_obj.render(text_entry,True, white,black)
			screen.blit(txt,(self.x1+10,self.y1+(count*self.entry_hight)+5))
			count += 1
			
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
			count = 0
			for entry in self.data:
				e_x1, e_x2, e_y1, e_y2 = self.x1+5, self.x1+495, self.y1+(count*self.entry_hight)+5, self.y1+((count+1)*self.entry_hight)+5
				e_dx,e_dy = e_x2-e_x1,e_y2-e_y1
				entry_points = ((e_x1,e_y1),(e_x2,e_y1),(e_x2,e_y2),(e_x1,e_y2))
				
				if inside_polygon(mouse_pos_x, mouse_pos_y,entry_points):
					self.selected = entry
					self.draw()
					pygame.draw.rect(screen,green, pygame.Rect((e_x1,e_y1,e_dx,e_dy)),1)
					
				count += 1






#specifically designed for a 16 relay setup
class relay_status_bar():
	global relay_state
	def __init__(self,pos,color):
		self.x1,self.y1 = pos
		self.r = 10
		self.spacing = 5
		self.color = color
		self.x2,self.y2 = pos[0]+(32*self.r)+(17*self.spacing),pos[1]+2*(self.r+self.spacing)
		self.relay_bool = []
		self.dx = self.x2-self.x1
		self.dy = self.y2-self.y1
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		
	def draw(self):
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,light_blue, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		self.relay_bool = []
		for i in range(len(relay_state)):
			pygame.draw.circle(screen,self.color,(self.x1+self.r+self.spacing+i*(2*self.r+self.spacing),self.y1+self.r+self.spacing),self.r,not int(relay_state[i]))
			
		
	def do(self,event):
		pass



"""SCREENS"""

#general screen parent class
class basic_screen():
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = " "
	
	def event_handle(self,event):
		mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
		for obj in self.objects:
			if inside_polygon(mouse_pos_x, mouse_pos_y,obj.points):
				obj.do(event)
			if event.type == UPDATE_TIME_EVENT or event.type == SENSOR_EVENT:
				obj.do(event)
		
	def draw(self):
		screen.fill((0,0,0))
		for obj in self.objects:
			obj.draw()




class mainscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Main Screen"
		
		#here is all the objects you want in the screen
		
		#buttons that take you to other screens
		rec_b_main = button_img_do((self.xmax-415,15),"MS on.png",donothing)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		
		
		#graphs of tem and humidity
		#rec_g_temp = button_rec_do((15,70),(800,400),light_blue,"temp graph",False,gotoscreen_Temp)
		temp_graph = time_graph((15,70),(800,400),60,90,100,max_data_points,green,"Tempurature","TE")
		humid_graph = time_graph((15,550),(800,400),60,110,100,max_data_points,light_blue,"Humidity","H1")
		
		#rec_g_humid = button_rec_do((15,550),(800,400),light_blue,"humidity graph",False,gotoscreen_Humid)
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		relay_status = relay_status_bar((500,15),light_blue)
		
		#rotating status display
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-300),"green_gear.png",1,donothing)
		
		
		
		
		
		#only objects in this list will be active (drawn)
		self.objects = [relay_status,humid_graph,temp_graph,rec_b_debug,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,rot_b_status]
		
		#only include this for first screen too be drawn
		self.draw()


class MCscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Manual Control"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC on.png",donothing)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		
		
		b_list = [[["1",False,donothing,donothing],["2",False,donothing,donothing],["3",False,donothing,donothing]],[["4",False,donothing,donothing],["5",False,donothing,donothing],["6",False,donothing,donothing],["7",False,donothing,donothing]],[["8",False,donothing,donothing],["9",False,donothing,donothing],["0",False,donothing,donothing]],[["*",False,donothing,donothing],["#",False,donothing,donothing],["A",False,donothing,donothing],["B",False,donothing,donothing]],[["C",False,donothing,donothing],["D",False,donothing,donothing],["Reset",False,donothing,donothing]]]
		hex_p = hex_pad((70,135),55,b_list,light_blue)
		
		
		
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		self.objects = [rec_b_debug,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,hex_p]


class tempscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Temp"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp on.png",donothing)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)


		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		self.objects = [rec_b_debug,rec_b_MC,rec_b_main,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time]


class humidscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Humidity"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity on.png",donothing)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		
		self.objects = [rec_b_debug,rec_b_MC,rec_b_main,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time]


class datetimescreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Date & Time"
		

		#all the objects in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT on.png",donothing)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		
		
		month_label = text_label((120,90),(100,25),"Month",light_blue)
		self.slide_wheel_month = round_slider_int((50,150),100, 20, light_blue, 1,12,1)
		day_label = text_label((420,90),(100,25),"Day",light_blue)
		self.slide_wheel_day = round_slider_int((350,150),100, 20, light_blue, 1,31,1)
		year_label = text_label((720,90),(100,25),"Year",light_blue)
		self.slide_wheel_year = round_slider_int((650,150),100, 20, light_blue, 2010,2050,2017)
		hour_label = text_label((120,490),(100,25),"Hours",light_blue)
		self.slide_wheel_hour = round_slider_int((50,550),100, 20, light_blue, 0,23,0)
		minute_label = text_label((420,490),(100,25),"Minutes",light_blue)
		self.slide_wheel_minute = round_slider_int((350,550),100, 20, light_blue, 0,59,0)
		second_label = text_label((720,490),(100,25),"Seconds",light_blue)
		self.slide_wheel_second = round_slider_int((650,550),100, 20, light_blue, 0,59,0)
		
		rec_b_getTime = button_img_do((self.xmax-530,695),"gettime.png",getTime)
		rec_b_setTime = button_img_do((self.xmax-530,785),"settime.png",setTime)
		
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		
		self.objects = [rec_b_debug,second_label,minute_label,hour_label,year_label,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time, self.slide_wheel_month,self.slide_wheel_day,self.slide_wheel_year,self.slide_wheel_hour,self.slide_wheel_minute,self.slide_wheel_second,rec_b_getTime,rec_b_setTime,month_label,day_label]

#currently the debugging screen
class debugscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Settings"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug on.png",donothing)
		
		
		
		
		
		
		screen_label = text_label((self.xmax/2-100,20),(200,35),"Debugging",light_blue)
		
		serial_label = text_label((175,65),(200,30),"Serial Log", white)
		debug_w = debug_window((50,100),serial_comm)
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		self.objects = [rec_b_debug,rec_b_MC,rec_b_ToDo,rec_b_humid,rec_b_temp,rec_b_datetime,rec_b_main,rec_l_date,rec_l_time,screen_label,debug_w,serial_label]


class ToDoscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "ToDo"
		
		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo on.png",donothing)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		
		self.todo_display = ToDo_window((100,100),settings_dict["ToDo"])
		img_b_new = button_img_do((630,115),"add.png",ToDo_new)
		img_b_del = button_img_do((630,235),"del.png",ToDo_del)
		img_b_edit = button_img_do((630,355),"edit.png",ToDo_change)
		
		
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		
		self.objects = [rec_b_debug,img_b_new,img_b_del,img_b_edit,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,self.todo_display]

#different from other screens. Must be passed an entry from ToDo list. Use [0,0,0,0,0] if "new"
class ToDoEditor(basic_screen):
	def __init__(self,entry):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "ToDo"
		self.entry = entry
		
		#here is all the objects you want in the screen
		
		hour_label = text_label((120,490),(100,25),"Hours",light_blue)
		self.slide_wheel_hour = round_slider_int((50,550),100, 20, light_blue, 0,23,self.entry[0])
		minute_label = text_label((420,490),(100,25),"Minutes",light_blue)
		self.slide_wheel_minute = round_slider_int((350,550),100, 20, light_blue, 0,59,self.entry[1])
		second_label = text_label((720,490),(100,25),"Seconds",light_blue)
		self.slide_wheel_second = round_slider_int((650,550),100, 20, light_blue, 0,59,self.entry[2])
		
		img_b_mis = button_img_do((1000,500),"MIS.png",ToDo_MIS)
		img_b_cancel = button_img_do((1000,600),"Cancel.png",gotoscreen_ToDo)
		
		b_list = [[[1,"1"],[2,"2"],[3,"3"],[4,"4"],[5,"5"],[6,"6"],[7,"7"],[8,"8"]],[[9,"9"],[10,"0"],[11,"A"],[12,"B"],[13,"C"],[14,"D"],[15,"*"],[16,"#"]]]
		self.round_tog_pad_relay = ellipse_toggle_pad((100,100),(75,75),5,b_list,light_blue,entry[3])
		
		
		b_list2 = [[[0,"OFF"],[1,"ON"]]]
		self.round_tog_pad_state = ellipse_toggle_pad((100,300),(75,75),5,b_list2,light_blue,entry[4])
		
		self.objects = [self.round_tog_pad_state,self.round_tog_pad_relay,img_b_mis,img_b_cancel, self.slide_wheel_second,self.slide_wheel_minute,self.slide_wheel_hour,second_label,minute_label,hour_label,second_label,minute_label,hour_label]




class paasscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Error 404"
		

		#here is all the objects you want in the screen
		img_b_cancel = button_img_do((self.xmax - 350,20),"Cancel.png",gotoscreen_Main)

		
		self.objects = [img_b_cancel]



#initialize screens and therefore their objects
main_s = mainscreen()
mc_s = MCscreen()
debug_s = debugscreen()
temp_s = tempscreen()
humid_s = humidscreen()
datetime_s = datetimescreen()
paas_s = paasscreen()
ToDo_s = ToDoscreen()
screen_dict = {"Main":main_s,"MC":mc_s,"Debug":debug_s,"Temp":temp_s,"Humid":humid_s,"DateTime":datetime_s,"paas":paas_s,"ToDo":ToDo_s}


current_screen = main_s






"""EVENT HANDLER"""
def event_handler(event):
	global current_screen
	global sample_temp_data
	global serial_comm
	global data_list
	#events without categories must come first in the elif chain
	if event.type == SENSOR_EVENT:
		#eventually this will be a get-sensor-data to the arduino and sorting of the received data into individual lists and an average
		new_data_set = [[7,0,0],round(triangular(65,90,75),1),round(triangular(70,100,80),1),round(triangular(65,90,75),1),round(triangular(70,100,80),1),round(triangular(65,90,75),1),round(triangular(70,100,80),1),round(triangular(65,90,75),1),round(triangular(70,100,80),1),"0000000000000000",False]
		data_list = new_data_set + data_list
		
		data_dict["TE"]=[new_data_set[1]] + data_dict["TE"]
		data_dict["T1"]=[new_data_set[2]] + data_dict["T1"]
		data_dict["H1"]=[new_data_set[3]] + data_dict["H1"]
		data_dict["T2"]=[new_data_set[4]] + data_dict["T2"]
		data_dict["H2"]=[new_data_set[5]] + data_dict["H2"]
		data_dict["T3"]=[new_data_set[6]] + data_dict["T3"]
		data_dict["H3"]=[new_data_set[7]] + data_dict["H3"]
		data_dict["T4"]=[new_data_set[8]] + data_dict["T4"]
		data_dict["H4"]=[new_data_set[9]] + data_dict["H4"]
		
		for key in data_dict:
			if len(data_dict[key])>max_data_points:
				data_dict[key] = data_dict[key][:max_data_points]
		
		
	elif event.category == "changescreen":
		current_screen = screen_dict[event.screen]
	

	
	elif event.category == "timeevent":
		
		if event == getTime:
			try:
				serial_send("<time>")
				rec_time_data = serial_recieve()
				clock.tick(60) #have to have a small delay as the pi is faster than the arduino and can send a new request before the arduino is ready for it
				serial_send("<date>")
				rec_date_data = serial_recieve()
				Y,M,D,H,m,S,MS = [int(x) for x in rec_date_data[0:-1].split(".")[::-1]+rec_time_data[0:-1].split(":")+[1]] #converting what was received from arduino into a list of Year,month,day,hour,min,sec,milisec
				global rawnow
				global setnow
				global nowadjust
				rawnow = datetime.datetime.now() #gets the systems version of time now
				setnow = datetime.datetime(Y,M,D,H,m,S,MS) #time to manually set your time to
				nowadjust = setnow - rawnow
			except:
				serial_comm.append("get time failed")
				

		elif event == setTime:
			
			year = datetime_s.slide_wheel_year.dial_output
			month = datetime_s.slide_wheel_month.dial_output.zfill(2)
			day = datetime_s.slide_wheel_day.dial_output.zfill(2)
			hour = datetime_s.slide_wheel_hour.dial_output.zfill(2)
			minute = datetime_s.slide_wheel_minute.dial_output.zfill(2)
			second = datetime_s.slide_wheel_second.dial_output.zfill(2)
			send_string = "<settime:"+year+":"+month+":"+day+":"+hour+":"+minute+":"+second+">"
			
			try:
				serial_send(send_string)
			except:
				serial_comm.append("set time failed")
	
	elif event.category == "todochange":
		
		global td_screen 
		if event == ToDo_new:
			TDE = ToDoEditor([0,0,0,0,0])
			td_screen = "new"
			current_screen = TDE
		elif event == ToDo_change:
			if ToDo_s.todo_display.selected == "none":
				pass
			else:
				td_screen = "edit"
				TDE = ToDoEditor(ToDo_s.todo_display.selected)
				current_screen = TDE
		elif event == ToDo_del:  
			if ToDo_s.todo_display.selected == "none":
				pass
			else:
				for i in range(len(settings_dict["ToDo"])):
					if settings_dict["ToDo"][i] == ToDo_s.todo_display.selected:
						del(settings_dict["ToDo"][i])
						ToDo_s.todo_display.selected = "none"
						break
				save_settings()
				current_screen.draw()
		if event == ToDo_MIS:
			new_entry = [int(current_screen.slide_wheel_hour.dial_output),int(current_screen.slide_wheel_minute.dial_output),int(current_screen.slide_wheel_second.dial_output),int(current_screen.round_tog_pad_relay.selected),int(current_screen.round_tog_pad_state.selected)]
			if td_screen == "new":
				settings_dict["ToDo"].append(new_entry)
				settings_dict["ToDo"] = sortlist(settings_dict["ToDo"])
			if td_screen == "edit":
				del(settings_dict["ToDo"][settings_dict["ToDo"].index(ToDo_s.todo_display.selected)])
				ToDo_s.todo_display.selected = "none"
				settings_dict["ToDo"].append(new_entry)
				settings_dict["ToDo"] = sortlist(settings_dict["ToDo"])
			save_settings()
			current_screen = ToDo_s




"""SETUP"""
"""runs once before main loop"""
serial_comm_start()

clock = pygame.time.Clock()

current_screen = main_s #boots to main screen

pygame.time.set_timer(UPDATE_TIME_EVENT, time_freq) #for updateing the time displayed
pygame.time.set_timer(SENSOR_EVENT, sensor_freq) #timer for getting sensor data

pygame.event.post(getTime) #gets the time from the arduino on startup





"""MAIN PROGRAM LOOP"""
while True:
    
    for event in pygame.event.get():
        screen_last = current_screen
        
        if event.type == pygame.QUIT:
            save_settings()
            exit()
            
        elif event.type == CUSTOMEVENT or event.type == SENSOR_EVENT:
            event_handler(event)
        
        current_screen.event_handle(event)
        if current_screen != screen_last:
            current_screen.draw()
            

    pygame.display.flip()    
    clock.tick(60)