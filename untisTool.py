#!/usr/bin/env python3
import webuntis
import pdb
import datetime, calendar
import logging


def main():
	logging.basicConfig(filename="",level=logging.DEBUG)
	logger = logging.getLogger("untisTool")
	config = loadConfig()
	if "untis" in config.sections():
		untisConfig = config["untis"]
		untisConfigKeys = untisConfig.keys()
		requiredKeys = ["url", "username", "password", "school"]
		if all(configKey in untisConfigKeys for configKey in requiredKeys):
			today = datetime.date.today()
			monday = today - datetime.timedelta(days=today.weekday())
			friday = monday + datetime.timedelta(days=4)
			untis = Untis(untisConfig["url"], untisConfig["school"], untisConfig["username"], untisConfig["password"])
			untisJson = untis.getUntisJson(monday, friday, "EI1c")

			nextMonday = monday + datetime.timedelta(days=7)
			nextFriday = friday + datetime.timedelta(days=7)
			untisJsonNextWeek = untis.getUntisJson(nextMonday, nextFriday, "EI1c")

			if "caldav" in config.sections():
				logger.info("starting to sync with caldav server")
				caldavConfig = config["caldav"]
				syncWithCaldav(untisJson, caldavConfig["url"], caldavConfig["username"], caldavConfig["password"])
				syncWithCaldav(untisJsonNextWeek, caldavConfig["url"], caldavConfig["username"], caldavConfig["password"])
				logger.info("syncing with server successfull.")
			else:
				logger.warning("No \"caldav\"-section in config file. Skipping upload to a caldav server!")

			logger.info("Everything done. Exiting now.")
			exit(0)

		else:
			for requiredKey in requiredKeys:
				if requiredKey not in untisConfigKeys:
					logger.error("required config key \"{}\" in section \"untis\" is missing!".format(requiredKey))
			exit(1)
	else:
		logger.error("No \"untis\"-section in config file. This is a required section to fetch untis data!")
		exit(1)



def loadConfig():
	import configparser
	logger = logging.getLogger("untisTool")
	logger.info("loading config from file \"config.ini\"")
	config = configparser.ConfigParser()
	config.read("config.ini")
	if len(config) <= 1:
		logger.error("loading config file failed. Maybe there is no such config?")
		exit(1)

	logger.info("loaded config successfully.")
	return config


def syncWithCaldav(week, url, username, password):
	import caldav
	from caldav.elements import dav, cdav

	client = caldav.DAVClient(url)
	client.username = username
	client.password = password
	principal = client.principal()
	calendars = principal.calendars()

	for day in list(calendar.day_name)[:-2]:
		for ttEvent in week[day.lower()]:
			icalstream = buildIcal(ttEvent)
			calendars[0].add_event(icalstream)


def buildIcal(untisEvent):
	import vobject
	cal = vobject.iCalendar()
	event = cal.add("vevent")
	event.add("summary").value = "{name} - {long_name}".format(name=untisEvent["name"], long_name=untisEvent["long_name"])
	event.add('uid').value = untisEvent["id"]
	event.add('dtstart').value = untisEvent["start"]
	event.add("dtend").value = untisEvent["end"]
	event.add("location").value = untisEvent["rooms"]
	icalstream = cal.serialize()

	return icalstream


class Untis():
	__useragent__ = "Test Useragent"

	def __init__(self, url, school, username, password):
		self.__logger__ = logging.getLogger("untisTool")
		self.__session__ = webuntis.Session(
				server = url,
				username = username,
				password = password,
				school = school,
				useragent = self.__useragent__
		)
		self.login()

	def login(self):
		self.__session__.login()

	def logout(self):
		self.__session__.logout()

	def getUntisObject(self, startDate, endDate, klasse=""):
		myClass = self.__session__.klassen().filter(name=klasse)[0]
		untisObject = self.__session__.timetable(klasse=myClass, start=startDate, end=endDate)
		return untisObject

	def getUntisJson(self, startDate, endDate, klasse=""):
		untisObject = self.getUntisObject(startDate, endDate, klasse)

		week = {
				"monday" : (),
				"tuesday" : (),
				"wednesday" : (),
				"thursday" : (),
				"friday" : ()
		}

		for course in untisObject:
			i = course
			name = ",".join(map(lambda e: e.name, i.subjects))
			long_name = ",".join(map(lambda e: e.long_name, i.subjects))
			klassen = ",".join(map(lambda e: e.name, i.klassen))
			rooms = ",".join(map(lambda e: e.name, i.rooms))
			start = i.start
			stop = i.end
			day = ({
					"index" : len(week[start.strftime("%A").lower()]),
					"id" : str(i.id),
					"name" : name,
					"long_name" : long_name,
					"klassen" : klassen,
					"rooms" : rooms,
					"start" : start,
					"end" : stop
					},)
			week[start.strftime("%A").lower()] += day

		# sort course in all weekdays by starttime
		for day in week.keys():
			week[day] = sorted(week[day], key=lambda k: k["start"])

		# !import code; code.interact(local=vars())

		return week



def getUntisData(untisUrl, school, untisUsername, untisPassword, startDate="this week monday", endDate="this week friday"):
	logger = logging.getLogger("untisTool")
	session = webuntis.Session(
			server = untisUrl,
			username = untisUsername,
			password = untisPassword,
			school = school,
			useragent = "Test"
	)

	session.login()

	my_class = session.klassen().filter(name="EI1c")[0]

	if isinstance(startDate, type(str())) or isinstance(endDate, type(str())):
		logger.warning("No date supplied for getUntisData(). Using monday of this week as start and friday of this week as end.")
		today = datetime.date.today()
		monday = today - datetime.timedelta(days=today.weekday())
		friday = monday + datetime.timedelta(days=4)
		startDate = monday
		endDate = friday

	# get data from untis
	tt = session.timetable(klasse=my_class, start=startDate, end=endDate)

	week = {
			"monday" : (),
			"tuesday" : (),
			"wednesday" : (),
			"thursday" : (),
			"friday" : ()
	}

	for course in tt:
		i = course
		name = ",".join(map(lambda e: e.name, i.subjects))
		long_name = ",".join(map(lambda e: e.long_name, i.subjects))
		klassen = ",".join(map(lambda e: e.name, i.klassen))
		rooms = ",".join(map(lambda e: e.name, i.rooms))
		start = i.start
		stop = i.end
		day = ({
				"index" : len(week[start.strftime("%A").lower()]),
				"id" : str(i.id),
				"name" : name,
				"long_name" : long_name,
				"klassen" : klassen,
				"rooms" : rooms,
				"start" : start,
				"end" : stop
				},)
		week[start.strftime("%A").lower()] += day

	# sort course in all weekdays by starttime
	for day in week.keys():
		week[day] = sorted(week[day], key=lambda k: k["start"])

	# !import code; code.interact(local=vars())

		# {'active': True, 'did': 6, 'name': 'EI1c', 'longName': 'Bachelor EI1c', 'id': 4872}
	session.logout()
	return week


main()
