import urllib
import json
import e4u
import base64

def shorten(url):
	url = urllib.urlopen("http://d.0l.de/add.json?type=URL&rdata=%s" % urllib.quote(url))
	response = url.read()
	response = json.loads(response)

	for entry in response:
		if entry['type'] == 'success':
			host = entry['data'][0]['host']
			return "http://s.%s/%s" % (host['zone']['name'], host['punycode'])


def ago(secs):
	periods = ["second", "minute", "hour", "day", "week", "month", "year", "decade"]
	lengths = [60, 60, 24, 7,4.35, 12, 10]

	j = 0
	diff = secs

	while diff >= lengths[j]:
		diff /= lengths[j]
		diff = round(diff)
		j += 1

	period = periods[j]
	if diff > 1: period += "s"

	return "%d %s ago" % (diff, period)

def softToUni(message):
	message = message.decode("utf-8")
	return e4u.translate(message, reverse=False, **e4u.SOFTBANK_TRANSLATE_PROFILE)

def decodePassword(password):
	return base64.b64decode(bytes(password.encode("utf-8")))
