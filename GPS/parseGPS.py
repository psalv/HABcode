#!/usr/bin/python3

###
# Connect to the GPS and parse the messages, pulling out the info we want to transmit.
#
###
import serial
import pynmea2
from subprocess import call
from time import sleep
from datetime import datetime
import csv

port = '/dev/ttyAMA0'
baud = 9600 # pulse rate of port
callSign = 'VE3UWO-1'

def getTimeAndDate():
	date = datetime.now()
	timestr = '{}:{}:{:02d}EDT'.format(date.hour, date.minute, date.second)
	datestr = '{}-{:02d}-{:02d}'.format(date.year, date.month, date.day)
	return (timestr, datestr)

def handleGPSmsg(GGAmsg, RMCmsg):
	"""
	GGAmsg is a pynmea2 parsed GGA string (http://www.gpsinformation.org/dale/nmea.htm#GGA)
	To see what fields are available see the pynmea2 docs (https://github.com/Knio/pynmea2)

	To get latitude in degrees for example you can do msg.latitude
	"""
	speed = RMCmsg.spd_over_grnd # speed in knots
	speed *= 0.514444 # speed in meters/sec

	msg = GGAmsg
	altitude = msg.altitude
	timestmp = msg.timestamp

	longitudeDecimal = '{:02.6f} {}'.format(msg.lon, msg.lon_dir)
	latitudeDecimal = '{:02.6f} {}'.format(msg.lat, msg.lat_dir)

	#longitude = '%02d°%02d′%07.4f″' % (msg.longitude, msg.longitude_minutes, msg.longitude_seconds)
	#latitude = '%02d°%02d′%07.4f″' % (msg.latitude, msg.latitude_minutes, msg.latitude_seconds)

	print(str(timestmp)+" UTC:", latitudeDecimal, longitudeDecimal, 'alt:', altitude, 'meters spd:', '{:.3f}'.format(speed), "m/s")

	message = "UTC: " + str(timestmp) +  "Latitude: " + str(latitudeDecimal) + " Longitude: " + str(longitudeDecimal) + " Altitude" + str(altitude) + " Speed: " + '{:.3f}'.format(speed) + "m/s"

	# transmit
	if not call(['aprs', '-c', callSign, '-o', 'packet.wav',  message]):
		print("APRS packet created with message: " + message)
	else:
		print("There was an error creating the APRS packet")

	if not call(['/home/pi/HABcode/GPS/sendAPRS.sh']):
		print("APRS packet sent!")
	else:
		print("APRS packet not sent!")

	# log gps data locally
	logfile = 'gpslog_{}.csv'.format(getTimeAndDate()[1])
	with open(logfile, 'a', 1) as csvfile:
		writer = csv.DictWriter(csvfile, fieldnames=['time', 'alt', 'lat', 'lng'])
		writer.writerow({'time': getTimeAndDate()[0], 'alt': str(altitude), 'lat': str(latitudeDecimal), 'lng': str(longitudeDecimal)})

	sleep(15)

def getGPSLogData():
	ser = serial.Serial(port, baud)
	GGAmsg = None # location info

	line = ser.readline()
	line = line.strip()
	try:
		line = line.decode('utf-8')
		msg = pynmea2.parse(line, check=False)
		if isinstance(msg, pynmea2.types.talker.GGA):
			GGAmsg = msg
		elif isinstance(msg, pynmea2.types.talker.RMC):
			return ('','','')
	except pynmea2.nmea.ChecksumError:
		print('ignoring checksum error')
	except pynmea2.nmea.ParseError:
		print('ignoring parse error')
	except UnicodeDecodeError:
		print('ignoring unicode error')
	finally:
		ser.close()
		return ('','','')

	if GGAmsg:
		msg = GGAmsg

		altitude  = str(msg.altitude)
		latitude  = '%02d°%02d′%07.4f″' % (msg.latitude, msg.latitude_minutes, msg.latitude_seconds)
		longitude = '%02d°%02d′%07.4f″' % (msg.longitude, msg.longitude_minutes, msg.longitude_seconds)
		return (altitude, latitude, longitude)
	else:
		return ('','','')


if __name__ == '__main__':
	# start local log
	logfile = 'gpslog_{}.csv'.format(getTimeAndDate()[1])
	with open(logfile, 'a', 1) as csvfile:
		writer = csv.DictWriter(csvfile, fieldnames=['time', 'alt', 'lat', 'lng'])
		writer.writeheader()

	ser = serial.Serial(port, baud)
	GGAmsg = None # location info
	RMCmsg = None # speed info
	try:
		while True:
			line = ser.readline()
			line = line.strip()
			try:
				line = line.decode('utf-8')
				msg = pynmea2.parse(line, check=False)
				if isinstance(msg, pynmea2.types.talker.GGA):
					GGAmsg = msg
				elif isinstance(msg, pynmea2.types.talker.RMC):
					RMCmsg = msg
			except pynmea2.nmea.ChecksumError:
				print('ignoring checksum error')
			except pynmea2.nmea.ParseError:
				print('ignoring parse error')
			except UnicodeDecodeError:
				print('ignoring unicode error')

			if GGAmsg and RMCmsg:
				handleGPSmsg(GGAmsg, RMCmsg)
				GGAmsg = None; RMCmsg = None

	finally:
		ser.close()
