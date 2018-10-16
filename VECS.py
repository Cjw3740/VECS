"""Must have also downloaded: pygame and pyserial"""



print("Vivarium Environmental Control System: V.E.C.S.")
print("Importing stuff")
import pygame
from math import *  #can limit this to just the functions you need when you're closer to being done
import datetime
import json
import serial
from random import randint,triangular, choice

print("Initializing Pygame")
pygame.init()

screen_size_x,screen_size_y  = 1600, 1000
screen = pygame.display.set_mode((screen_size_x,screen_size_y))


time_freq = 100 #freq for updating the time 1000 = 1sec
sensor_freq = 1000 #get sensor val. 1000 = 1sec, should be set to 5 sec for actual use

#serial communications stuff
serial_comm = ["startup"]
serial_comm_max_len = 40
serial_comm_established = False
Arduino_address = '/dev/ttyACM0'


try:
	ser = serial.Serial(Arduino_address, 9600,timeout=1) # Establish the connection on a specific port, must know the name of the arduino port
	serial_comm.append("serial comm sucessfull")
	serial_comm_established = True
except:
	print('serial comm failed')
	serial_comm.append("serial comm failed")
	serial_comm_established = False


print("Getting time")
sys_now = datetime.datetime.now() #gets the systems version of time now
set_now = datetime.datetime(2018, 9, 21, 6, 00, 1, 1) #default time, to be overwritten by time obtained from Arduino
now_adjustment = set_now - sys_now  #adjusted time


"""Relay/ToDo stuff"""
relay_state = "0000000000000000"
original_RS = ""

manual_control_engaged = False
ToDo = []
settings_dict = {}


overrides = {"NN":"2222222222222222",'HN':"2222222222222222","CN":"2222222222222222", "ND":"2222222222222222", "NW":"2222222222222222", "HD":"2222222222222222", "HW":"0222222222222222", "CD":"1222222222222222", "CW":"2222222222222222"}
override_dict = {"T":[80.0,70.5],"H":[99.0,70.0]}
relay_dict = {1:"Lights",2:"Mister",3:"Fog 1",4:"Fog Fan 1",5:"Fogger 2",6:"Fog Fan 2",7:"Air Fan",8:"H20 Pump",9:"unused",10:"unused",11:"unused",12:"unused",13:"unused",14:"unused",15:"unused",16:"unused"}



override_names = ['NN','HN','CN','NW','HW','CW','ND','HD','CD']
current_override_state = "NN"

"""sensor related stuff"""
num_sensors = 2 #eventually number of connected sensors will be dynamic



#max number of points to save in each small sensor reading list
max_data_points = 100
#dict for holdingt sensor data TE = example temp. Initialize with dummy value so that plot works on new startup?
data_dict = {
"T1":[],
"H1":[],
"T2":[],
"H2":[],
"T3":[],
"H3":[],
"T4":[],
"H4":[],
"TA":[],
"HA":[],
"TH":[0],
"TL":[500],
"TE":[0],
"HH":[0],
"HL":[500],
"HE":[0]}




"""new sceme for handling data. Send Aurduino a 'get all' command and it shuld return date,relay state, and T/H pairs, Manual control indicator, and Override state as text in the 
following format: 'YYYY:MM:DD:HH:mm:SS-0000000000000000-TT.T/HH.H:TT.T/HH.H-M-OR' 
'-' deliniate the different sections, ':' different sub sections, and '/' seperated temp humidity pairs. 
Bad sensor readings should be stored as 'error'
Temp sensors can't give data more frequently thanonce every 2 sec, so say 5 sec between readings. This amounts to 56 bytes per reading for 2 sensors
roughly 17,800 sensor readings for a megabyte of data, or roughly 24 hours of data collected. 
Save every 24 hours at/near midnight.
Override states: NN - nominal, HN - hot, CN - cold, ND - dry, NW - wet, HD -hot/dry, HW - hot/wet, CD - cold/dry, CW - cold/wet
inbetween saves the data should be stored in the varialble 'data_log'"""

data_log = ["2018:10:10:03:02:01-0000000000000000-75.5/65.5:76.0/66.0-0-NN"]


print("Setting up text options")
#setting up text options (needs to be cleaned up, some use msg_obj some use font)
pygame.font.init()  #must call this
msg_obj = pygame.font.SysFont('New Times Roman', 30) #msg object to render, font and size
font = pygame.font.Font(None,30)


print("defining colors")
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


print("Setting up custom events")
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
gotoscreen_Override = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Override')
gotoscreen_Settings = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Settings')
gotoscreen_Relaynames = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Relaynames')
gotoscreen_Serial = pygame.event.Event(CUSTOMEVENT, category = 'changescreen', screen = 'Serial')

ToDo_change = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'edit')
ToDo_new = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'new')
ToDo_del = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'delete')
ToDo_MIS = pygame.event.Event(CUSTOMEVENT, category = 'todochange', action = 'MIS')

getTime = pygame.event.Event(CUSTOMEVENT, category = 'timeevent', action = 'getTime')
setTime = pygame.event.Event(CUSTOMEVENT, category = 'timeevent', action = 'setTime')

MC_enable = pygame.event.Event(CUSTOMEVENT, category = 'manualcontrol', action = 'enable')
MC_disable = pygame.event.Event(CUSTOMEVENT, category = 'manualcontrol', action = 'disable')
MC_reset = pygame.event.Event(CUSTOMEVENT, category = 'manualcontrol', action = 'reset')

getSensorData = pygame.event.Event(CUSTOMEVENT, category = 'timeevent', action = 'getsensordata')

clear_temp_tracking = pygame.event.Event(CUSTOMEVENT, category = 'clearsensordata',ation = "temp")
clear_hum_tracking = pygame.event.Event(CUSTOMEVENT, category = 'clearsensordata',action = "hum")

start_serial_comms = pygame.event.Event(CUSTOMEVENT, category = 'serial',action = "start")
stop_serial_comms = pygame.event.Event(CUSTOMEVENT, category = 'serial',action = "stop")
ORrelay_update = pygame.event.Event(CUSTOMEVENT, category = 'serial',action = "uploadOR")

override_select = pygame.event.Event(CUSTOMEVENT, category = 'overrideselect')
override_set = pygame.event.Event(CUSTOMEVENT, category = 'overrideset')


save_settings_manual = pygame.event.Event(CUSTOMEVENT, category = 'savesettings')

donothing = pygame.event.Event(CUSTOMEVENT, category = 'donothing')

UPDATE_TIME_EVENT = pygame.USEREVENT+2
SENSOR_EVENT = pygame.USEREVENT+3





"""for tracking outgoing serial communications to arduino. To be used in place of ser.write"""
def serial_send(str_data):
	global serial_comm
	serial_comm.append("Pi:" + str_data)
	if serial_comm_established:
		ser.write(str_data.encode())
	else:
		serial_comm.append("Serial Comms down")
	if len(serial_comm) > serial_comm_max_len:
			del serial_comm[0]

"""for tracking incomming serial communications from arduino. To be used in place of ser.readline"""
def serial_recieve():
	global serial_comm
	if serial_comm_established:
		
		recieved = ser.readline().decode('ascii')[:-1]   #the slice removes the newline
		serial_comm.append("Arduino:" + recieved[:-1])
		return recieved
	else:
		return False
		#serial_comm.append("Serial Comms down")
	if len(serial_comm) > serial_comm_max_len:
			del serial_comm[0]


"""sets up serial com with arduino"""
def serial_comm_start():
	try:
		global ser
		ser = serial.Serial(Arduino_address, 9600,timeout=1) # Establish the connection on a specific port, must know the name of the arduino port
		serial_comm.append("serial comm sucessfull")
		serial_comm_established = True
	except:
		serial_comm.append("serial comm failed")



#decided to allways have a response from the Arduino, so might as well combine the send/recieve functions into one
def arduino_send_rec(str_msg):
	global serial_comm
	serial_comm.append("Pi:" + str_msg)
	if serial_comm_established:
		try:
			ser.write(str_msg.encode())
			try:
				recieved = ser.readline().decode('ascii')[:-2]   #the slice removes the newline
				if not recieved:
					serial_comm.append("No response")
				else:
					serial_comm.append("Arduino:" + recieved)
				
				return recieved
			except:
				serial_comm.append("Recieve failed")
				
		except:
			serial_comm.append("Send failed")
		
	else:
		serial_comm.append("Serial Comms down")
	
	while len(serial_comm) > serial_comm_max_len:
		del serial_comm[0]
	
	
	
	
	








def get_str_now():
	tempnow = now_adjustment + datetime.datetime.now()
	return tempnow.strftime("%m/%d/%y  %H:%M:%S")

def get_str_time_now():
	tempnow = now_adjustment + datetime.datetime.now()
	return tempnow.strftime("%H:%M:%S")

def get_str_date_now():
	tempnow = now_adjustment + datetime.datetime.now()
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

#assumes now is a list of h,m,s. Figures out what the current relay state should be
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
	with open('Settings.txt','w') as outfile:
		json.dump(settings_dict, outfile)
		outfile.close

#need to add backup settings to use if no save fileis found
def load_settings():
	global settings_dict
	with open('Settings.txt','r') as infile:
		settings_dict = json.load(infile)
		infile.close

load_settings()

def save_datalog():
	name = ".".join([data_log[-1][0:18],'txt'])
	with open(name,'w') as outfile:
		json.dump(data_log, outfile)
		outfile.close


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
		self.button_text_size = font.size(self.text)
		self.button_txt_loc = (self.center[0]-self.button_text_size[0]/2,self.center[1]-self.button_text_size[1]/2) #sets up text options for button label
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



#keypad of square buttons, only one of which can be selected at any given time, specifically to be used for controling the override state to be set by the 3 state relay table
class Override_toggle_pad():
	def __init__(self,loc,button_size,button_color,boarder_color):
		self.dx,self.dy = button_size*3,button_size*3
		self.button_names = [['Nominal','Hot','Cold'],['Wet','Hot/Wet','Cold/Wet'],['Dry','Hot/Dry','Cold/Dry']]
		self.x1,self.y1 = loc
		self.x2,self.y2 = self.x1 + self.dx,self.y1 +self.dy
		self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
		self.button_color = button_color
		self.boarder_color = boarder_color
		self.buttons = [button_rec_tog((self.x1+i*button_size,self.y1+j*button_size),(button_size,button_size),button_color,self.button_names[j][i],False,override_select,donothing) for i in range(3) for j in range(3)]
		self.buttons[0].pressed = True

	def draw(self):
		
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		for i,button in enumerate(self.buttons):
			button.draw()
	
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
			for button in self.buttons:
				if inside_polygon(mouse_pos_x, mouse_pos_y,button.points):
					button.do(event)
				else:
					button.pressed = False
			self.draw()


class Override_relay_pad():
	def __init__(self,loc,btn_size):
		self.btn_x,self.btn_y = btn_size[0],btn_size[1]
		self.dx,self.dy = (self.btn_x*2,self.btn_y*8)
		#self.button_names = [['Nominal','Hot','Cold'],['Wet','Hot/Wet','Cold/Wet'],['Dry','Hot/Dry','Cold/Dry']]
		self.x1,self.y1 = loc
		self.x2,self.y2 = self.x1 + self.dx,self.y1 +self.dy
		self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
		#self.button_color = button_color
		#self.boarder_color = boarder_color
		#grid of 3 state buttons for setting relay overrides
		self.buttons = [button_rec_3state((self.x1+j*self.btn_x,self.y1+i*self.btn_y),(self.btn_x,self.btn_y),light_blue,black,white,green,settings_dict["relay_dict"][str((1+i)+(8*j))],2,override_set,override_set,override_set) for j in range(2) for i in range(8)]
		
		#self.buttons = [button_rec_tog((self.x1+i*button_size,self.y1+j*button_size),(button_size,button_size),button_color,self.button_names[j][i],False,override_select,donothing) for i in range(3) for j in range(3)]
		self.buttons[0].pressed = True

	def draw(self):
		
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		for i,button in enumerate(self.buttons):
			button.text = settings_dict["relay_dict"][str(i+1)]
			button.draw()
	
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
			for button in self.buttons:
				if inside_polygon(mouse_pos_x, mouse_pos_y,button.points):
					button.do(event)
				else:
					button.pressed = False
			self.draw()




class button_rec_3state():
	#a 3 state button with a boarder
	def __init__(self,loc,size,boarder_color,color0,color1,color2,text,default_state,do_state0,do_state1,do_state2):
		self.loc = loc
		self.do_state1 = do_state1
		self.do_state2 = do_state2
		self.do_state0 = do_state0
		self.color1 = color1
		self.color2=color2
		self.color0=color0
		self.boarder_color = boarder_color
		self.dx,self.dy = size
		self.x1 = loc[0]
		self.y1 = loc[1]
		self.x2 = self.x1 + size[0]
		self.y2 = self.y1 +size[1]
		self.points = (self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)
		self.current_state = default_state #states should be 1,2 or 3
		self.text = text
		self.color = [color0,color1,color2][default_state]
		self.boarder = 0 #don't think I even need this for this button
		self.order = {0:1,1:2,2:0}

	def draw(self):
		
		
		
		
		if self.current_state == 0:
			self.color = self.color0

		elif self.current_state == 1:
			self.color = self.color1

		elif self.current_state == 2:
			self.color = self.color2
			
		
		if self.color == black:
			txt_col = white
		else:
			txt_col = black
		txt = msg_obj.render(self.text,True, txt_col, self.color)
		
		self.txt_loc = (self.x1 + self.dx/2 - font.size(self.text)[0]/2,self.y1 + self.dy/2 - font.size(self.text)[1]/2)
		
		
		pygame.draw.rect(screen,self.boarder_color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,black, pygame.Rect((self.x1+2,self.y1+2,self.dx-4,self.dy-4)))
		pygame.draw.rect(screen,self.color, pygame.Rect((self.x1+2,self.y1+2,self.dx-4,self.dy-4)),0)
		screen.blit(txt,self.txt_loc)
	
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			self.current_state = self.order[self.current_state]
			self.draw()
			pygame.event.post([self.do_state0,self.do_state1,self.do_state2][self.current_state])



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



class minmax_slider(control):
	def __init__(self, size, min_val, max_val, min_color, max_color, min_diff, position,target):
		self.x1,self.y1 = position
		if size[0]%2: #ensures the width is an odd number so the exact center can be the vertical slider line
			self.center = self.x1 + round(size[0]/2)+1
			self.size = size
		else:
			self.center = self.x1 + size[0]/2+1
			self.size = (size[0]+1,size[1])
			
		self.x2,self.y2=self.x1 + size[0],self.y1 +size[1]
		self.dx,self.dy = self.x2 - self.x1,self.y2 - self.y1
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)) #the active box that constitutes the control
		self.slider_loc = position #this is the upper left corner of the active box. The max and min text boxes will be outside this as they don't need to be blacked out every frame
		self.text_size = font.size(str(max_val)) #getting the max dimensions of text it will display
		self.slider_len = size[1]
		self.min_val = min_val
		self.max_val = max_val
		self.min_diff = min_diff #minimum difference between max and min slider
		self.target = target #the entry in override_dict it will affect
		self.val_range = max_val - min_val
		self.slider_txt_box = (size[0],30)
		self.xp,self.yp = 0,0
		self.m = (self.y2-self.y1)/(min_val-max_val)
		self.b = self.y2 - (self.y2-self.y1)/(1-(max_val/min_val))
		
	def mv(self,val):
		return int(max(min(val*self.m+self.b,self.y2-1),self.y1+1))


	def draw(self):
		global settings_dict
		pygame.draw.rect(screen,black,pygame.Rect((self.x1,self.y1-self.text_size[1],self.dx,self.dy+self.text_size[1]+20)),0) #blacks out box
		pygame.draw.line(screen,white,(self.center,self.y1),(self.center,self.y2),1) #draws slider center line
		pygame.draw.line(screen,white,(self.center-5,self.y1),(self.center+5,self.y1),1) #draws top horizontal bar
		pygame.draw.line(screen,white,(self.center-5,self.y2),(self.center+5,self.y2),1) #draws bottom horizontal bar
		pygame.draw.rect(screen,white,pygame.Rect((self.center-self.slider_txt_box[0]/2,self.y1-self.slider_txt_box[1]-13,self.slider_txt_box[0],self.slider_txt_box[1])),1) #draws max text box
		pygame.draw.rect(screen,white,pygame.Rect((self.center-self.slider_txt_box[0]/2,self.y2+14,self.slider_txt_box[0],self.slider_txt_box[1])),1) #draws min text box
		max_txt = msg_obj.render(str(self.max_val),True,white,black) #max text
		min_txt = msg_obj.render(str(self.min_val),True,white,black) #min text
		screen.blit(max_txt,(self.center-font.size(str(self.max_val))[0]/2,self.y1-self.slider_txt_box[1]-17+font.size(str(self.max_val))[1]/2))
		screen.blit(min_txt,(self.center-font.size(str(self.min_val))[0]/2,self.y2+20))
		
		right_pos_y = self.mv(settings_dict["override_dict"][self.target][0])
		right_triangle = [(self.center+1,right_pos_y),(self.center+10,right_pos_y-10),(self.center+10,right_pos_y+10)]
		left_pos_y = self.mv(settings_dict["override_dict"][self.target][1])
		left_triangle = [(self.center-1,left_pos_y),(self.center-10,left_pos_y-10),(self.center-10,left_pos_y+10)]
		
		pygame.draw.polygon(screen, red,right_triangle,0) #right slider triangle
		pygame.draw.rect(screen,red,pygame.Rect(self.center+12,right_pos_y-13,font.size('100.0')[0]+4,self.text_size[1]+6),1) #right slider text box
		pygame.draw.polygon(screen, blue,left_triangle,0) #left slider triangle
		pygame.draw.rect(screen,blue,pygame.Rect(self.center-12,left_pos_y-13,-font.size('100.0')[0]-4,self.text_size[1]+6),1) #right slider text box
		
		slider_right_txt = msg_obj.render(str(round(settings_dict["override_dict"][self.target][0],1)),True,white,black)
		slider_left_txt = msg_obj.render(str(round(settings_dict["override_dict"][self.target][1],1)),True,white,black)
		
		screen.blit(slider_right_txt, (self.center+20,right_pos_y-8))
		screen.blit(slider_left_txt, (self.center-60,left_pos_y-8))
		

	def do(self,event):
		global settings_dict
		mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
		if pygame.mouse.get_pressed()[0] and inside_polygon(mouse_pos_x, mouse_pos_y,self.points):
			if mouse_pos_x > self.center:
				settings_dict["override_dict"][self.target][0] = max((1/self.m)*(mouse_pos_y - self.b),self.min_val+self.min_diff)
				settings_dict["override_dict"][self.target][1] = min(settings_dict["override_dict"][self.target][1],settings_dict["override_dict"][self.target][0]-self.min_diff)
			else:
				settings_dict["override_dict"][self.target][1] = min((1/self.m)*(mouse_pos_y - self.b),self.max_val-self.min_diff)
				settings_dict["override_dict"][self.target][0] = max(settings_dict["override_dict"][self.target][0],settings_dict["override_dict"][self.target][1]+self.min_diff)
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


#keypad control using toggle buttons
class hex_pad_RS():
	global relay_state
	
	
	def __init__(self,initial_point,side_len,color):
		self.xo,self.yo = initial_point
		self.side_len = side_len
		self.buttons_list = [[[settings_dict["relay_dict"][str(1+i+(3*j))],False,donothing,donothing] for i in range(3+j%2)] for j in range(5)]
		self.buttons_list[-1][-1][0] = "Reset"
		self.rows = int(len(self.buttons_list))
		self.cols_list = [int(len(self.buttons_list[i])) for i in range(self.rows)]
		self.color = color
		self.hx = int(self.side_len * (sqrt(3))/2)
		self.hy = int(self.side_len/2)
		self.points = ((self.xo-int(1.5*self.hx),self.yo-self.hy),(self.xo+4*max(self.cols_list)*self.hx,self.yo-self.hy),(self.xo+2*max(self.cols_list)*self.hx,self.yo+5*self.hy*self.rows),(self.xo-self.hx,self.yo+5*self.hy*self.rows))
		self.buttons = []
		
		for j in range(self.rows):
			for i in range(len(self.buttons_list[j])):
				self.buttons.append(button_hex_tog((self.xo+int(2.2*i*self.hx)-int(1.12*(j%2)*self.hx),self.yo+int(3.3*j*self.hy)),self.side_len,self.color,self.buttons_list[j][i][0],self.buttons_list[j][i][1],self.buttons_list[j][i][2],self.buttons_list[j][i][3]))
		
		self.buttons[-1].do_pressed = MC_reset #sets the last button in the list to be the reset button
		
	def draw(self):
		for i,key in enumerate(self.buttons):
			if i < len(relay_state):
				key.pressed = int(relay_state[i])
				key.text = settings_dict["relay_dict"][str(i+1)]
			key.draw()
	

	def do(self,event):
		global relay_state
		if event.type == UPDATE_TIME_EVENT:
			self.draw()
		mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
		for btn in self.buttons:
			if inside_polygon(mouse_pos_x, mouse_pos_y,btn.points):
				btn.do(event) 
		
		if manual_control_engaged:
			relay_state = "".join(str(int(self.buttons[i].pressed)) for i in range(len(relay_state)))
			


class keyboard():
	def __init__(self,loc,size,color,do_on_complete):
		self.x1,self.y1 = loc
		self.dx,self.dy = size
		self.x2,self.y2 = self.x1+self.dx,self.y1+self.dy
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2)) 
		self.keys_lower = '1234567890qwertyuiopasdfghjklzxcvbnm. '
		self.keys_upper = '!@#$%^&*()QWERTYUIOPASDFGHJKLZXCVBNM? '
		self.special_keys = ['BckSpc','CAPS','Space','Clear','Enter']
		self.output = []
		self.caps = False
		self.max_len = 10
		self.key_x = int(self.dx/10)
		self.key_y = int(self.dy/5)
		self.color = color
		self.do_on_complete = do_on_complete
		
		#building the keyboard as a single demensional list of buttons
		#lower: 1234567890qwertyuiopasdfghjklzxcvbnm. bckspc caps caps cancel space enter
		#upper !@#$%^&*()QWERTYUIOPASDFGHJKLZXCVBNM? bckspc caps caps cancel space enter
		#the letter keys don't technically need to be initialized to any particular value, as it will re-write with actual values with every draw
		self.keys = [button_rec_do((self.x1+(i*self.key_x),self.y1+j*self.key_y),(self.key_x,self.key_y),self.color,self.keys_lower[i+(10*j)],False,donothing) for j in range(3) for i in range(10)]
		del(self.keys[-1])

		fourth_row = [button_rec_do((self.x1+(i*self.key_x),self.y1+3*self.key_y),(self.key_x,self.key_y),self.color,self.keys_lower[i+(10*3)-2],False,donothing) for i in range(1,9)] #adding 4th row keys
		for b in fourth_row:
			self.keys.append(b)
		
		self.keys.append(button_rec_do((self.x1+9*self.key_x,self.y1+2*self.key_y),(self.key_x,self.key_y),self.color,self.special_keys[0],False,donothing)) #adding backspace key
		self.keys.append(button_rec_do((self.x1,self.y1+3*self.key_y),(self.key_x,self.key_y),self.color,self.special_keys[1],False,donothing)) #adding left CAPS key
		self.keys.append(button_rec_do((self.x1+9*self.key_x,self.y1+3*self.key_y),(self.key_x,self.key_y),self.color,self.special_keys[1],False,donothing)) #adding right CAPS key
		self.keys.append(button_rec_do((self.x1,self.y1+4*self.key_y),(2*self.key_x,self.key_y),self.color,self.special_keys[3],False,donothing)) #adding Cancel
		self.keys.append(button_rec_do((self.x1+2*self.key_x,self.y1+4*self.key_y),(6*self.key_x,self.key_y),self.color,self.special_keys[2],False,donothing)) #adding Space
		self.keys.append(button_rec_do((self.x1+8*self.key_x,self.y1+4*self.key_y),(2*self.key_x,self.key_y),self.color,self.special_keys[4],False,donothing)) #adding Enter
		
		
		
		
	def draw(self):
		
		#Could seperate out the output window rather than redrawing every key on every mouse click, esxcept the CAPS keys
		pygame.draw.rect(screen,black, pygame.Rect((self.x1+int(self.dx/2)-105,self.y1-115,210,50)))
		pygame.draw.rect(screen,self.color, pygame.Rect((self.x1+int(self.dx/2)-105,self.y1-115,210,50)),1)
		txt = msg_obj.render("".join(self.output),True, self.color, black)
		screen.blit(txt,(self.x1+int(self.dx/2)-100,self.y1-100))
		
		
		for i,k in enumerate(self.keys):
			if i<=36:
				if self.caps == True:
					k.text = self.keys_upper[i]
				else:
					k.text = self.keys_lower[i]
		
		
		
		for btn in self.keys:
			btn.draw()
		
	def do(self,event):
		if event.type == pygame.MOUSEBUTTONDOWN:
			mouse_pos_x,mouse_pos_y = pygame.mouse.get_pos()
			for btn in self.keys:
				if inside_polygon(mouse_pos_x, mouse_pos_y,btn.points):
					if btn.text == "CAPS":
						self.keys[38].pressed = not self.keys[38].pressed
						self.keys[39].pressed = not self.keys[39].pressed
						self.caps = not self.caps
						
					elif btn.text == "BckSpc":
						if len(self.output):
							del(self.output[-1])
						
					elif btn.text == "Enter": #this manually resets the text in the relay dict and the relay pad ont his screen. Need to tie other relay pad's text into relay dict directly so they update on draw... did so for MC relay pad. Need to create custom class for override relay table
						settings_dict["relay_dict"][str(current_screen.round_tog_pad_relay.selected+1)] = "".join(self.output)
						current_screen.round_tog_pad_relay.buttons[current_screen.round_tog_pad_relay.selected].text = settings_dict["relay_dict"][str(current_screen.round_tog_pad_relay.selected+1)] 
						current_screen.round_tog_pad_relay.draw()
						
					elif btn.text == 'Clear':
						self.output = []
						
						
					elif btn.text == "Space":
						if len(self.output)<10:  #this should be based on the actual size of the text...
							self.output.append(" ")
					
					elif len(self.output)<10:
						self.output.append(btn.text)
			self.draw()







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
							self.selected = self.buttons.index(button)
						else:
							button.pressed = False
						
			self.draw()




"""example button list: 
b_list = [[[1,"1"],[2'"2"][3,"Three"]],
[[4,"4],[5,"5"]],
[[6,"6"]]]
number to output then label
"""
class ellipse_relay_pad():
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
		self.buttons = b_list = [[[i+(8*j),settings_dict["relay_dict"][str(1+i+(8*j))]] for i in range(8)] for j in range(2)]
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
							self.selected = self.buttons.index(button)
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
			


class sensor_label():
	def __init__(self,loc,size,color,label,target):
		self.loc = loc
		self.size = size
		self.color = color
		self.dx,self.dy = size
		self.x1 = loc[0]
		self.y1 = loc[1]
		self.x2 = self.x1 + size[0]
		self.y2 = self.y1 +size[1]
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x1,self.y2),(self.x2,self.y2))
		self.target = target
		self.label = label
		

	def draw(self):
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		if len(data_dict[self.target]):
			self.text = self.label + ': ' + str(data_dict[self.target][0])

		else: 
			self.text = "0"
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
		
		self.h_ov = settings_dict["override_dict"][target[0]][0]
		self.l_ov = settings_dict["override_dict"][target[0]][1]
		
			
		
	#function for mapping a value into y-coord, bound within the max and min of the graph
	def mv(self,val):
		if isinstance(val,str): #if val is an error, just put it in the middle of the screen
			return int((self.y2-self.y1)/2 +self.y1)
		else:
			return int(max(min(val*self.m+self.b,self.y2-1),self.y1+1))
		
		
	def plot(self):
		global settings_dict
		self.h_ov = settings_dict["override_dict"][self.target[0]][0]
		self.l_ov = settings_dict["override_dict"][self.target[0]][1]
		
		pygame.draw.rect(screen,black, pygame.Rect((self.x1+1,self.y1+1,self.dx-2,self.dy-2)),0) #blacks out graph area
		pygame.draw.rect(screen,black, pygame.Rect((self.x2+1,self.y1-16,85,self.dy+32)),0) #blacks out area to right of graph, currently seperate to make it clear, should ultimatly be combined with above line
		
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
		pygame.draw.polygon(screen, red, ((self.x2+2,self.mv(self.h_ov)),(self.x2+17,self.mv(self.h_ov)-15),(self.x2+17,self.mv(self.h_ov)+15)),1) #triabgle
		pygame.draw.polygon(screen, red, ((self.x2+20,self.mv(self.h_ov)-15),(self.x2+20,self.mv(self.h_ov)+15),(self.x2+85,self.mv(self.h_ov)+15),(self.x2+85,self.mv(self.h_ov)-15)),1) #box
		data_txt = msg_obj.render(str(round(self.h_ov,1)),False, red, black)
		txt_loc =  (self.x2+27,self.mv(self.h_ov)-11)
		screen.blit(data_txt,txt_loc)
		#low override
		pygame.draw.polygon(screen, blue, ((self.x2+2,self.mv(self.l_ov)),(self.x2+17,self.mv(self.l_ov)-15),(self.x2+17,self.mv(self.l_ov)+15)),1)
		pygame.draw.polygon(screen, blue, ((self.x2+20,self.mv(self.l_ov)-15),(self.x2+20,self.mv(self.l_ov)+15),(self.x2+85,self.mv(self.l_ov)+15),(self.x2+85,self.mv(self.l_ov)-15)),1)
		data_txt = msg_obj.render(str(round(self.l_ov,1)),False, blue, black)
		txt_loc =  (self.x2+27,self.mv(self.l_ov)-11)
		screen.blit(data_txt,txt_loc)
		
		
		if len(self.data)>=1: #draws the most current reading
			pygame.draw.polygon(screen, white, ((self.x2+2,self.mv(self.data[0])),(self.x2+17,self.mv(self.data[0])-15),(self.x2+17,self.mv(self.data[0])+15)),1)
			pygame.draw.polygon(screen, white, ((self.x2+20,self.mv(self.data[0])-15),(self.x2+20,self.mv(self.data[0])+15),(self.x2+85,self.mv(self.data[0])+15),(self.x2+85,self.mv(self.data[0])-15)),1)
			if self.data[0] == 'error':
				txt_col = yellow
			elif self.data[0] >= self.h_ov:
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


class serial_window():
	def __init__(self,pos,ser_com):
		self.x1,self.y1 = pos
		self.data = ser_com
		self.x2,self.y2 = (self.x1+780,self.y1+((serial_comm_max_len+1)*font.size("Example")[1]))
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
			
			text_entry = hms[0]+":"+hms[1]+":"+hms[2]+"  "+settings_dict["relay_dict"][str(entry[3]+1)]+"  "+rs
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
					pygame.draw.rect(screen,green, pygame.Rect((e_x1,e_y1,e_dx,e_dy)),1) #this needs tio be moved into the draw command, based on whats selected
					
				count += 1






#specifically designed for a 16 relay setup
class relay_status_bar():
	global relay_state
	def __init__(self,pos):
		self.x1,self.y1 = pos
		self.r = 10
		self.spacing = 5
		self.color = light_blue
		self.x2,self.y2 = pos[0]+(32*self.r)+(17*self.spacing),pos[1]+2*(self.r+self.spacing)
		self.relay_bool = []
		self.dx = self.x2-self.x1
		self.dy = self.y2-self.y1
		self.points = ((self.x1,self.y1),(self.x2,self.y1),(self.x2,self.y2),(self.x1,self.y2))
		
	def draw(self):
		global manual_control_engaged
		if manual_control_engaged:
			self.color = yellow
		else:
			self.color = light_blue
		pygame.draw.rect(screen,black, pygame.Rect((self.x1,self.y1,self.dx,self.dy)))
		pygame.draw.rect(screen,self.color, pygame.Rect((self.x1,self.y1,self.dx,self.dy)),1)
		self.relay_bool = []
		for i in range(len(relay_state)):
			pygame.draw.circle(screen,self.color,(self.x1+self.r+self.spacing+i*(2*self.r+self.spacing),self.y1+self.r+self.spacing),self.r,not int(relay_state[i]))
			
		
	def do(self,event):
		if event.type == UPDATE_TIME_EVENT:
			self.draw()



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
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)
		
		
		#graphs of tem and humidity
		#rec_g_temp = button_rec_do((15,70),(800,400),light_blue,"temp graph",False,gotoscreen_Temp)
		ta_label = text_label((300,60),(200,30),"Average Temp",light_blue)
		temp_graph = time_graph((15,100),(800,400),60,90,100,max_data_points,green,"Tempurature","TA")
		ha_label = text_label((300,540),(200,30),"Average Humidity",light_blue)
		humid_graph = time_graph((15,580),(800,400),60,110,100,max_data_points,light_blue,"Humidity","HA")
		
		#rec_g_humid = button_rec_do((15,550),(800,400),light_blue,"humidity graph",False,gotoscreen_Humid)
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		rec_l_temp = sensor_label((250,15),(200,30),light_blue,"Temperature","TA")
		rec_l_hum = sensor_label((950,15),(200,30),light_blue,"Humidity","TA")
		
		relay_status = relay_status_bar((500,15))
		
		#rotating status display
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)
		
		
		
		
		
		#only objects in this list will be active (drawn)
		self.objects = [rec_b_override,ha_label,ta_label,relay_status,humid_graph,temp_graph,rec_b_debug,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,rot_b_status,rec_l_temp,rec_l_hum]
		
		#only include this for first screen too be drawn
		self.draw()


class MCscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Manual Control"
		self.warning = "*WARNING* Enabling manual control suspends all automated tasks, including environmental overrides! Disable when done!"

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC on.png",donothing)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)

		hex_p = hex_pad_RS((150,150),80,light_blue)
		
		relay_status = relay_status_bar((500,15))
		
		MC_tog = button_rec_tog((800,350),(250,200),yellow,"MANUAL CONTROL",False,MC_enable,MC_disable)
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		rec_l_temp = sensor_label((250,15),(200,30),light_blue,"Temperature","TA")
		rec_l_hum = sensor_label((950,15),(200,30),light_blue,"Humidity","TA")
		
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)
		
		self.objects = [rot_b_status,rec_b_override,rec_l_hum,rec_l_temp,rec_b_debug,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,relay_status,MC_tog,hex_p]


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
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)

		
		
		#Temp graphs. hight should depend on number of sensors and screensize: hight=(screenY-2*top/bottombuffer-2inbetweenbuffer)/(num_sensors+1)
		ta_label = text_label((300,60),(200,30),"Average Temp",light_blue)
		temp_graphA = time_graph((15,100),(800,220),60,90,100,max_data_points,green,"Tempurature","TA")
		t1_label = text_label((300,380),(200,30),"Temp Sensor 1",light_blue)
		temp_graph1 = time_graph((15,420),(800,220),60,90,100,max_data_points,green,"Tempurature","T1")
		t2_label = text_label((300,700),(200,30),"Temp Sensor 2",light_blue)
		temp_graph2 = time_graph((15,740),(800,220),60,90,100,max_data_points,green,"Tempurature","T2")
		
		#max/min temp
		high_temp_l = sensor_label((950,150),(200,30),light_blue,"High Temp","TH")
		low_temp_l = sensor_label((950,200),(200,30),light_blue,"Low Temp","TL")
		error_temp = sensor_label((950,250),(200,30),yellow,"Errors","TE")
		
		clear_temp_data = button_rec_do((950,350),(200,90),purple,"Clear H/L/E",False,clear_temp_tracking)

		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		relay_status = relay_status_bar((500,15))
		
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)
		
		self.objects = [rot_b_status,rec_b_override,error_temp,clear_temp_data,low_temp_l,high_temp_l,rec_b_debug,rec_b_MC,rec_b_main,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,t1_label,temp_graph1,t2_label,temp_graph2,ta_label,temp_graphA,relay_status]


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
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)

		
		ha_label = text_label((300,60),(200,30),"Average Humidity",light_blue)
		humid_graphA = time_graph((15,100),(800,220),60,110,100,max_data_points,light_blue,"Humidity","HA")
		h1_label = text_label((300,380),(200,30),"Humidity Sensor 1",light_blue)
		humid_graph1 = time_graph((15,420),(800,220),60,110,100,max_data_points,light_blue,"Humidity","H1")
		h2_label = text_label((300,700),(200,30),"Humidity Sensor 2",light_blue)
		humid_graph2 = time_graph((15,740),(800,220),60,110,100,max_data_points,light_blue,"Humidity","H2")
		
		
		high_hum_l = sensor_label((950,150),(200,30),light_blue,"High Humidity","HH")
		low_hum_l = sensor_label((950,200),(200,30),light_blue,"Low Humidity","HL")
		error_hum = sensor_label((950,250),(200,30),yellow,"Errors","HE")
		
		clear_temp_data = button_rec_do((950,350),(200,90),purple,"Clear H/L/E",False,clear_hum_tracking)
		
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		relay_status = relay_status_bar((500,15))
		
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)
		
		self.objects = [rot_b_status,rec_b_override,clear_temp_data,error_hum,low_hum_l,high_hum_l,rec_b_debug,rec_b_MC,rec_b_main,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,humid_graph1,humid_graph2,humid_graphA,ha_label,h1_label,h2_label,relay_status]


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
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)

		
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
		
		rec_b_getTime = button_img_do((90,self.ymax - 150),"gettime.png",getTime)
		rec_b_setTime = button_img_do((500,self.ymax - 150),"settime.png",setTime)
		
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)

		
		self.objects = [rot_b_status,rec_b_override,rec_b_debug,second_label,minute_label,hour_label,year_label,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time, self.slide_wheel_month,self.slide_wheel_day,self.slide_wheel_year,self.slide_wheel_hour,self.slide_wheel_minute,self.slide_wheel_second,rec_b_getTime,rec_b_setTime,month_label,day_label]

#currently the debugging screen
class debugscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Debugging"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug on.png",donothing)
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)
		
		screen_label = text_label((self.xmax/2-100,20),(200,35),"Debugging",light_blue)
		
		serial_label = text_label((175,65),(200,30),"Serial Log", white)
		debug_w = serial_window((50,100),serial_comm)
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)
		
		self.objects = [rot_b_status,rec_b_override,rec_b_debug,rec_b_MC,rec_b_ToDo,rec_b_humid,rec_b_temp,rec_b_datetime,rec_b_main,rec_l_date,rec_l_time,screen_label,debug_w,serial_label]


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
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)
		
		
		self.todo_display = ToDo_window((100,100),settings_dict["ToDo"])
		img_b_new = button_img_do((630,115),"add.png",ToDo_new)
		img_b_del = button_img_do((630,235),"del.png",ToDo_del)
		img_b_edit = button_img_do((630,355),"edit.png",ToDo_change)
		
		
		
		#time and date
		rec_l_date = date_label((15,15),(100,30),light_blue)
		rec_l_time = time_label((130,15),(100,30),light_blue)
		
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)
		
		self.objects = [rot_b_status,rec_b_override,rec_b_debug,img_b_new,img_b_del,img_b_edit,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_ToDo,rec_l_date,rec_l_time,self.todo_display]

#different from other screens. Must be passed an entry from ToDo list. Use [0,0,0,0,0] if "new"
class ToDoEditor(basic_screen):
	def __init__(self,entry):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "ToDo"
		self.entry = entry
		
		#here is all the objects you want in the screen
		
		#these positions should be based on the screen dimensions
		hour_label = text_label((270,490),(100,25),"Hours",light_blue)
		self.slide_wheel_hour = round_slider_int((140,550),150, 30, light_blue, 0,23,self.entry[0])
		minute_label = text_label((730,490),(100,25),"Minutes",light_blue)
		self.slide_wheel_minute = round_slider_int((600,550),150, 30, light_blue, 0,59,self.entry[1])
		second_label = text_label((1230,490),(100,25),"Seconds",light_blue)
		self.slide_wheel_second = round_slider_int((1100,550),150, 30, light_blue, 0,59,self.entry[2])
		
		img_b_mis = button_img_do((1200,100),"MIS.png",ToDo_MIS)
		img_b_cancel = button_img_do((1300,200),"Cancel.png",gotoscreen_ToDo)
		
		#list of relays
		b_list = [[[i+(8*j),settings_dict["relay_dict"][str(1+i+(8*j))]] for i in range(8)] for j in range(2)]
		self.round_tog_pad_relay = ellipse_toggle_pad((100,50),(120,120),5,b_list,light_blue,entry[3])
		
		#on/off
		b_list2 = [[[0,"OFF"],[1,"ON"]]]
		self.round_tog_pad_state = ellipse_toggle_pad((100,350),(90,90),10,b_list2,light_blue,entry[4])
		
		self.objects = [self.round_tog_pad_state,self.round_tog_pad_relay,img_b_mis,img_b_cancel, self.slide_wheel_second,self.slide_wheel_minute,self.slide_wheel_hour,second_label,minute_label,hour_label,second_label,minute_label,hour_label]



class Overridescreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Overrides"
		
		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		rec_b_override = button_img_do((self.xmax-415,615),"overrides on.png",donothing)
		
		
		temp_label = text_label((50,60),(137,40),"Temp",light_blue)
		OR_slider_temp = minmax_slider((137,300),50,100,blue,red,5,(50,150),"T")
		hum_label = text_label((50,560),(137,40),"Humidity",light_blue)
		OR_slider_hum = minmax_slider((137,300),50,100,blue,red,5,(50,650),"H")
		
		self.OR_table = Override_toggle_pad((250,200),150,light_blue,white) #lists the various override states in a 3 by 3 grid
		
		self.relay_pad = Override_relay_pad((800,80),(110,110)) #the list of 3 state buttons for the override relay states
		
		rec_b_upload = button_rec_do((250,700),(450,150),orange,"Upload to Arduino",False,donothing)
		
		
		
		
		rot_b_status = rot_image_button((self.xmax-300,self.ymax-250),"green_gear.png",1,gotoscreen_Settings)
		
		#all the objects you want to render
		self.objects = [rec_b_upload,rot_b_status,self.OR_table,self.relay_pad, hum_label,temp_label,rec_b_debug,rec_b_main,rec_b_MC,rec_b_datetime,rec_b_temp,rec_b_humid,rec_b_override,rec_b_ToDo,OR_slider_temp,OR_slider_hum]


class settingsscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Settings"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_temp = button_img_do((self.xmax-415,95),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,175),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,255),"ToDo off.png",gotoscreen_ToDo)
		rec_b_override = button_img_do((self.xmax-415,335),"overrides off.png",gotoscreen_Override)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		
		settings_title= text_label((150,10),(700,30),"Settings", white)
		
		
		rec_b_relaynames = button_ellipse_do((100,100),(200,100),red,"Rename Relays",False,gotoscreen_Relaynames) #takes you to a screen where you can rename the individual relays
		rec_b_sensorsettings = button_ellipse_do((100,250),(200,100),blue,"Sensor Settings",False,donothing) #will eventually take you to a screen where you can set the frequency of get all calls to the arduino, manually dump the data_log, ect. 
		rec_b_manualsave = button_ellipse_do((100,400),(200,100),purple,"Save Settings",False,save_settings_manual) #manually saves settings. It automatically saves on exit but this would prevent loss in the event of a crash
		rec_b_serial = button_ellipse_do((100,550),(200,100),orange,"Serial Comms",False,gotoscreen_Serial)
		rec_b_datetime = button_ellipse_do((100,700),(200,100),light_blue,"Date & Time",False,gotoscreen_DateTime)
		
		
		self.objects = [settings_title,rec_b_datetime,rec_b_serial,rec_b_manualsave,rec_b_sensorsettings,rec_b_override,rec_b_MC,rec_b_ToDo,rec_b_humid,rec_b_temp,rec_b_main,rec_b_relaynames]


class serialscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Serial Comms"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)
		
		
		
		serial_label = text_label((50,65),(750,30),"Recent Serial Communication", white)
		debug_w = serial_window((20,100),serial_comm)
		
		#these will be set up when the real arduino function is built
		reestablish_b = button_rec_do((820,75),(300,80),orange,"Reestablish Comms",False,start_serial_comms)
		close_link_b = button_rec_do((820,175),(300,80),orange,"Close Serial Comms",False,stop_serial_comms)
		upload_b = button_rec_do((820,275),(300,80),orange,"Upload All Settings",False,ORrelay_update)
		
		self.objects = [close_link_b,upload_b,reestablish_b,serial_label,debug_w,rec_b_override,rec_b_debug,rec_b_MC,rec_b_ToDo,rec_b_humid,rec_b_temp,rec_b_datetime,rec_b_main]






class relayrenamescreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Relay Names"
		

		#here is all the objects you want in the screen
		rec_b_main = button_img_do((self.xmax-415,15),"MS off.png",gotoscreen_Main)
		rec_b_datetime = button_img_do((self.xmax-415,95),"DT off.png",gotoscreen_DateTime)
		rec_b_temp = button_img_do((self.xmax-415,175),"Temp off.png",gotoscreen_Temp)
		rec_b_humid = button_img_do((self.xmax-415,255),"Humidity off.png",gotoscreen_Humid)
		rec_b_ToDo = button_img_do((self.xmax-415,335),"ToDo off.png",gotoscreen_ToDo)
		rec_b_MC = button_img_do((self.xmax-415,415),"MC off.png",gotoscreen_MC)
		rec_b_debug = button_img_do((self.xmax-415,535),"Debug off.png",gotoscreen_Debug)
		rec_b_override = button_img_do((self.xmax-415,615),"overrides off.png",gotoscreen_Override)
		
		
		#list of relays # toggle pad
		b_list = [[[i+(8*j),settings_dict["relay_dict"][str(1+i+(8*j))]] for i in range(8)] for j in range(2)]
		self.round_tog_pad_relay = ellipse_toggle_pad((50,50),(120,120),5,b_list,light_blue,0)
		
		
		
		relay_name_keyboard = keyboard((10,500),(self.xmax-500,400),light_blue,donothing)
		
		self.objects = [rec_b_override,rec_b_debug,rec_b_MC,rec_b_ToDo,rec_b_humid,rec_b_temp,rec_b_datetime,rec_b_main,relay_name_keyboard,self.round_tog_pad_relay]




class paasscreen(basic_screen):
	def __init__(self):
		self.xmax = screen_size_x
		self.ymax = screen_size_y
		self.name = "Error 404"
		

		#here is all the objects you want in the screen
		img_b_cancel = button_img_do((self.xmax - 350,20),"Cancel.png",gotoscreen_Main)

		
		self.objects = [img_b_cancel]



"""Arduino sim for coding without an actual arduino connected, and Arduino real for final version. Both should take same input and output the same format"""
"""'YYYY:MM:DD:HH:mm:SS-0000000000000000-TT.T/HH.H:TT.T/HH.H-M-OR' is the format for data obtained from the arduino
M is the manual control indicator bit 0 is off, 1 is MC engaged
OR is the override state

"""
def arduino_control(cmd_type,cmd_specific):
	global serial_comm
	global now_adjustment
	global sys_now
	global manual_control_engaged
	if cmd_type =="get":
		
		if cmd_specific == "all":
			reply = arduino_send_rec("<GA>")
			if reply:
				data_log.append(reply)
				
		elif cmd_specific == "time":
			reply = arduino_send_rec("<GT>")
			if reply:
				YYYY,MM,DD,hh,mm,ss = reply.split(":")
				sys_now = datetime.datetime.now() #gets the systems version of time now
				set_now = datetime.datetime(int(YYYY), int(MM), int(DD), int(hh), int(mm), int(ss), 0) #default time, to be overwritten by time obtained from Arduino
				now_adjustment = set_now - sys_now 
				
				
	elif cmd_type == "set":
		
		if cmd_specific == "datetime":
			year = datetime_s.slide_wheel_year.dial_output
			month = str(datetime_s.slide_wheel_month.dial_output).zfill(2)
			day = datetime_s.slide_wheel_day.dial_output.zfill(2)
			hour = datetime_s.slide_wheel_hour.dial_output.zfill(2)
			minute = datetime_s.slide_wheel_minute.dial_output.zfill(2)
			second = datetime_s.slide_wheel_second.dial_output.zfill(2)
			sys_now = datetime.datetime.now() #gets the systems version of time now
			set_now = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second), 0) #what you want the time to be
			now_adjustment = set_now - sys_now  #the nessesary adjustment to the system time for it to be the time you want
			send_string = "<ST"+year+month+day+hour+minute+second+">"
			reply = arduino_send_rec(send_string)
			if reply:
				data_log.append(reply)
			
		elif cmd_specific == "overrides":
			send_str = "SO"+str(settings_dict["override_dict"]["T"][0])+str(settings_dict["override_dict"]["T"][1])+str(settings_dict["override_dict"]["H"][0])+str(settings_dict["override_dict"]["H"][1])
			arduino_send_rec(send_str)
			
		elif cmd_specific == "ORrelaystate":
			if arduino_send_rec("SOSTART") == "SENDOR":
				for i in range(9): 
					arduino_send_rec(settings_dict["overrides"]["NN", "HN", "CN", "NW", "HW", "CW", "ND", "HD", "CD"][i])
				if arduino_send_rec("SOSTOP") == "ORRECIEVED":
					serial_comm.append("Override send complete")
			else:
				serial_comm.append("Override update failed")
			
		elif cmd_specific == "ToDo":
			pass 
			
			
	elif cmd_type == "MC":
		
		#the response to these needs to be tied directly to MC = True/False
		if cmd_specific == "on":
			arduino_send_rec("MC1")
			
		elif cmd_specific == "off":
			arduino_send_rec("MC0")
			
		elif cmd_specific == "set":
			arduino_send_rec("MC"+relay_state)

	
	elif cmd_type == "establish":
		serial_comm_start()






#initialize screens and therefore their objects
main_s = mainscreen()
mc_s = MCscreen()
debug_s = debugscreen()
temp_s = tempscreen()
humid_s = humidscreen()
datetime_s = datetimescreen()
paas_s = paasscreen()
ToDo_s = ToDoscreen()
or_s = Overridescreen()
settings_s = settingsscreen()
relaynames_s = relayrenamescreen()
serial_s = serialscreen()
screen_dict = {"Main":main_s,"MC":mc_s,"Debug":debug_s,"Temp":temp_s,"Humid":humid_s,"DateTime":datetime_s,"paas":paas_s,"ToDo":ToDo_s,"Override":or_s,"Settings":settings_s,"Relaynames":relaynames_s,"Serial":serial_s}


current_screen = main_s






"""EVENT HANDLER"""
def event_handler(event):
	global current_screen
	global data_log
	global serial_comm
	global manual_control_engaged
	global relay_state
	global override_names 
	global current_override_state
	#events without categories must come first in the elif chain
	if event.type == SENSOR_EVENT:
		#eventually this will be a get-sensor-data to the arduino and sorting of the received data into individual lists and an average
		if serial_comm_established:
			arduino_control("get","all")
			#parsing the data from the last Arduino get
			SD=data_log[-1].split('-')[2]
			
		
			#putting sensor readings into their appropriate sub lists for graphing. Need to generalize this into a single for loop based on num_sensors
			
			temp_total = 0
			hum_total = 0
			successful_temp_reads = 0
			successful_hum_reads = 0
			
			
			
			t1 = SD.split(':')[0].split('/')[0]
			if t1=='error':
				data_dict["T1"]=[t1] + data_dict["T1"]
				data_dict["TE"][0] += 1
			else:
				data_dict["T1"]=[float(t1)] + data_dict["T1"]
				temp_total += float(t1)
				successful_temp_reads +=1
				if float(t1)>data_dict["TH"][0]:
					data_dict["TH"][0]=float(t1)
				if float(t1)<data_dict["TL"][0]:
					data_dict["TL"][0]=float(t1)
			
			t2 = SD.split(':')[1].split('/')[0]
			if t2=='error':
				data_dict["T2"]=[t2] + data_dict["T2"]
				data_dict["TE"][0] += 1
			else:
				data_dict["T2"]=[float(t2)] + data_dict["T2"]
				temp_total += float(t2)
				successful_temp_reads +=1
				if float(t2)>data_dict["TH"][0]:
					data_dict["TH"][0]=float(t2)
				if float(t2)<data_dict["TL"][0]:
					data_dict["TL"][0]=float(t2)
				
				
			h1 = SD.split(':')[0].split('/')[1]
			if h1=='error':
				data_dict["H1"]=[h1] + data_dict["H1"]
				data_dict["HE"][0] += 1
			else:
				data_dict["H1"]=[float(h1)] + data_dict["H1"]
				hum_total += float(h1)
				successful_hum_reads +=1
				if float(h1)>data_dict["HH"][0]:
					data_dict["HH"][0]=float(h1)
				if float(h1)<data_dict["HL"][0]:
					data_dict["HL"][0]=float(h1)
			h2 = SD.split(':')[1].split('/')[1]
			if h2=='error':
				data_dict["H2"]=[h2] + data_dict["H2"]
				data_dict["HE"][0] += 1
				
			else:
				data_dict["H2"]=[float(h2)] + data_dict["H2"]
				hum_total += float(h2)
				successful_hum_reads +=1
				if float(h2)>data_dict["HH"][0]:
					data_dict["HH"][0]=float(h2)
				if float(h2)<data_dict["HL"][0]:
					data_dict["HL"][0]=float(h2)
			
			if successful_temp_reads:
				temp_avg = temp_total/successful_temp_reads
			else:
				temp_avg = 'error'
			
			if successful_hum_reads:
				hum_avg = hum_total/successful_hum_reads
			else:
				hum_avg = 'error'
			
			data_dict["TA"]=[temp_avg] + data_dict["TA"]
			data_dict["HA"]=[hum_avg] + data_dict["HA"]
			
			relay_state = data_log[-1].split('-')[1]
			
			
			for key in data_dict:
				if len(data_dict[key])>max_data_points:
					data_dict[key] = data_dict[key][:max_data_points]
			
		
	elif event.category == "changescreen":
		current_screen = screen_dict[event.screen]
		
	#this needs to be replaced/removed. Just take the time from the get all
	elif event.category == "timeevent":
		
		if event == getTime:
			arduino_control("get","time")
				
				
		elif event == setTime:
			if int(current_screen.slide_wheel_year.dial_output)==2011 and int(current_screen.slide_wheel_month.dial_output)==3 and int(current_screen.slide_wheel_day.dial_output)==12:
				current_screen = paas_s
			else:
				arduino_control("set","datetime")

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
	
	#this could be made into an if - else, but leaving explicit for clarity's sake
	elif event.category == "manualcontrol":
		global original_RS
		if event == MC_enable:
			manual_control_engaged = True
			#original_RS = ""
			original_RS = "".join(i for i in relay_state)
		elif event == MC_disable:
			original_RS = ""
			manual_control_engaged = False
		elif event == MC_reset:
			relay_state = "".join(i for i in original_RS)
			for i,n in enumerate(original_RS):
				mc_s.objects[-1].buttons[i].pressed=bool(int(n))
			mc_s.objects[-1].buttons[-1].pressed = False
	
	elif event.category == 'clearsensordata':
		if event == clear_temp_tracking:
			data_dict["TH"][0] = 0
			data_dict["TL"][0] = 500
			data_dict["TE"][0] = 0
		if event == clear_hum_tracking:
			data_dict["HH"][0] = 0
			data_dict["HL"][0] = 500
			data_dict["HE"][0] = 0
			
	#when selecting an override state, it draws the correct relay config
	elif event.category == "overrideselect":
		for i,b in enumerate(or_s.OR_table.buttons):
			if b.pressed == True:
				current_override_state = override_names[i]
				for j,btn in enumerate(or_s.relay_pad.buttons):
					btn.current_state = int(settings_dict["overrides"][override_names[i]][j])
					btn.draw()
	
	elif event.category == "overrideset":
		settings_dict["overrides"][current_override_state] = "".join(str(btn.current_state) for btn in or_s.relay_pad.buttons)
	
	elif event.category == "savesettings":
		save_settings()
	
	elif event.category == "serial":
		
		if event.action == "start":
			serial_comm_start()
		elif event.action == "stop":
			try:
				ser.close()
				serial_comm.append("Serial comms stopped")
			except:
				serial_comm.append("Error closing serial port")
		elif event.action == "uploadOR":
			arduino_control("set","ORrelaystate")





"""SETUP"""
"""runs once before main loop"""
#serial_comm_start()

clock = pygame.time.Clock()

current_screen = main_s #boots to main screen

pygame.time.set_timer(UPDATE_TIME_EVENT, time_freq) #for updateing the time displayed
pygame.time.set_timer(SENSOR_EVENT, sensor_freq) #timer for getting sensor data

#pygame.event.post(getTime) #gets the time from the arduino on startup





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

