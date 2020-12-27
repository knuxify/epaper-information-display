#!/usr/bin/env python3
from evdev import InputDevice, categorize, ecodes
import time
import asyncio
import atexit

# For display 0
import datetime

# For display 2
import platform
import distro
import socket
import gpiozero
import subprocess # Also used for display 1

import RPi.GPIO as GPIO

from waveshare.epaper import EPaper
from waveshare.epaper import Handshake
from waveshare.epaper import RefreshAndUpdate
from waveshare.epaper import SetPallet
from waveshare.epaper import FillRectangle
from waveshare.epaper import DisplayText
from waveshare.epaper import SetCurrentDisplayRotation
from waveshare.epaper import SetEnFontSize
from waveshare.epaper import ClearScreen

sleep_length = 20

dev = InputDevice('/dev/input/event0')
dev.grab()

#####################
# Utility functions #
#####################

async def pause():
	"""
	Robust pause function that pauses until:
	- the left or right key is pressed
	- 20 seconds pass
	- the time changes (Display 0)
	"""
	async def keyboard(dev):
		async for event in dev.async_read_loop():
			if event.type == ecodes.EV_KEY and event.value == 1:
				#if event.code == 108:
				#	print("down")
				#elif event.code == 103:
				#	print("up")
				if event.code == 105:
					return "previous"
				elif event.code == 106:
					return "next"
				elif event.code == 28:
					return True
	async def timer():
		await asyncio.sleep(sleep_length)
		return "next"
	async def minute_timer():
		current_time = datetime.datetime.now()
		new_minute = int(current_time.strftime('%M')) + 1
		while True:
			current_time = datetime.datetime.now()
			current_minute = int(current_time.strftime('%M'))
			if current_minute != new_minute:
				await asyncio.sleep(1)
			else:
				return True
	keyboard_task = asyncio.create_task(keyboard(dev))
	timer_task = asyncio.create_task(timer())
	tasks = [keyboard_task, timer_task]
	if current_display_num == 0:
		minute_timer_task = asyncio.create_task(minute_timer())
		tasks.append(minute_timer_task)

	done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
	for task in pending:
		task.cancel()
	return done


def multiline_print(x, y, string, font_size, paper):
	"""
	Prints a multi-line message and accounts for line-breaks.
	Splits long messages into multiline messages.
	"""
	lines = [[]]
	lineno = 0
	charno = 0
	y = y - 10 - font_size
	for word in string.split():
		charno = charno + len(word) + 1
		if charno > 34:
			charno = 0
			printable = " ".join(lines[lineno])
			y = y + 10 + font_size
			lineno = lineno + 1
			lines.append([])
			paper.send(DisplayText(x, y, printable.encode("gb2312")))
		lines[lineno].append(word)
	y = y + 10 + font_size
	printable = " ".join(lines[lineno])
	paper.send(DisplayText(x, y, printable.encode("gb2312")))

############
# Displays #
############

def display_0(paper):
	"""
	Display 0: Clock, date
	"""
	current_time = datetime.datetime.now()

	paper.send(SetPallet(SetPallet.BLACK, SetPallet.WHITE))
	paper.send(SetEnFontSize(SetEnFontSize.SIXTYFOUR))
	paper.send(DisplayText(20, 464, str(current_time.strftime('%H:%M')).encode("gb2312")))
	paper.send(SetEnFontSize(SetEnFontSize.FOURTYEIGHT))
	paper.send(DisplayText(20, 532, str(current_time.strftime('%A, %d %B %Y')).encode("gb2312")))

def display_1(paper):
	"""
	Display 1: MOTD/Fortune
	"""
	fortune = ""
	paper.send(SetPallet(SetPallet.BLACK, SetPallet.WHITE))
	paper.send(SetEnFontSize(SetEnFontSize.SIXTYFOUR))
	paper.send(DisplayText(20, 20, "Message Of The Now:".encode("gb2312")))
	paper.send(SetPallet(SetPallet.DARK_GRAY, SetPallet.WHITE))
	paper.send(FillRectangle(20, 94, 780, 96))
	paper.send(SetPallet(SetPallet.BLACK, SetPallet.WHITE))
	paper.send(SetEnFontSize(SetEnFontSize.FOURTYEIGHT))
	fortune = str(subprocess.Popen("fortune", stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()[0])[2:-1].replace('\\t',' ').replace('\\n',' ')
	multiline_print(20, 110, fortune, 48, paper)

def display_2(paper):
	"""
	Display 2: Pi Status
	"""
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	try:
		# doesn't even have to be reachable
		s.connect(('10.255.255.255', 1))
		system_ip = s.getsockname()[0]
	except Exception:
		system_ip = 'N/A'
	finally:
		s.close()

	ping = subprocess.run(['ping', '-c1', '192.168.1.104']).stdout
	if ping == "ping: 192.168.1.104: Name or service not known":
		hc_status = "OFFLINE"
	else:
		ping2 = subprocess.run('curl https://192.168.1.104/nextcloud/ocs/v1.php/cloud/capabilities -X GET -H "OCS-APIRequest: true" -L -k | grep "502 Bad Gateway"', shell=True).returncode
		if ping2 == 0:
			hc_status = "PHP DEAD"
		else:
			hc_status = "Online"

	paper.send(SetPallet(SetPallet.BLACK, SetPallet.WHITE))
	paper.send(SetEnFontSize(SetEnFontSize.FOURTYEIGHT))
	paper.send(DisplayText(20, 20, str(platform.node() + " on " + distro.name()).encode("gb2312")))
	paper.send(SetPallet(SetPallet.DARK_GRAY, SetPallet.WHITE))
	paper.send(FillRectangle(20, 72, 780, 74))
	paper.send(SetPallet(SetPallet.BLACK, SetPallet.WHITE))
	paper.send(DisplayText(20, 90, str("CPU temperature : " + str(round(gpiozero.CPUTemperature().temperature, 2)) + "°").encode("gb2312")))
	# Degree character is broken and leaves a space between itself and "C".
	# Workaround: draw the "C" separately.
	paper.send(DisplayText(490, 90, str("C").encode("gb2312")))
	paper.send(DisplayText(20, 148, str("IP : " + system_ip).encode("gb2312")))
	paper.send(DisplayText(20, 206, str("Home cloud status : " + hc_status).encode("gb2312")))

displays = [display_0, display_1, display_2]

#################
# Main function #
#################

def exit_handler():
	dev.ungrab()
	paper.send(ClearScreen())
	paper.send(RefreshAndUpdate())

if __name__ == '__main__':
	with EPaper() as paper:
		atexit.register(exit_handler)
		paper.send(Handshake())
		time.sleep(2)
		paper.send(SetCurrentDisplayRotation(SetCurrentDisplayRotation.NORMAL))
		current_display_num = 0
		current_display = displays[current_display_num]
		while True:
			paper.read_responses(timeout=10)
			current_display(paper)
			paper.send(RefreshAndUpdate())

			paper.send(ClearScreen())
			pause_output = list(asyncio.run(pause()))[0].result()
			if pause_output == "previous":
				current_display_num = current_display_num - 1
			elif pause_output == "next":
				current_display_num = current_display_num + 1
			if current_display_num == len(displays):
				current_display_num = 0
			if current_display_num == -1:
				current_display_num = len(displays) - 1
			current_display = displays[current_display_num]

			paper.send(ClearScreen())
