#!/usr/bin/python

import os
import sys
import cgi
import cgitb
import time
import pycurl
import StringIO
import json
import sipgate

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from constants import *

def send_sms(recipient, content):
	sg = sipgate.api(SIPGATE_USERNAME, SIPGATE_PASSWORD, 'transwhat')

	default_uri = 'sip:NULL@sipgate.net'
	for own_uri in sg.OwnUriListGet()['OwnUriList']:
		if own_uri['DefaultUri']:
			default_uri = own_uri['SipUri']

	# SessionInitiate may return the following server status codes in case of errors: 501, 502, 506, 520, 525
	return sg.SessionInitiate({'LocalUri': default_uri, 'RemoteUri': 'sip:%s@sipgate.de' % recipient, 'TOS': 'text', 'Content': content })

def main():
	url = os.environ['SCRIPT_URI'] + '?' + os.environ['QUERY_STRING']

	writer = StringIO.StringIO()
	ch = pycurl.Curl()

	ch.setopt(pycurl.URL, url)
	ch.setopt(pycurl.USERAGENT, os.environ['HTTP_USER_AGENT'])

	ch.setopt(pycurl.WRITEFUNCTION, writer.write)
	ch.setopt(pycurl.SSL_VERIFYPEER, False)
	ch.setopt(pycurl.HEADER, True)

	ch.perform()

	response = writer.getvalue()
	headers, body = response.split("\r\n\r\n", 1)
	headers = headers.split("\n")
	preamble = headers.pop(0)

	code = preamble.split(" ", 2)[1]
	status = preamble.split(" ", 2)[2]

	print "Status: %s %s" % (code, status)
	for header in headers:
		print header

	print
	print body

	file = open(REQUESTS_FILE, "a")
	file.write("\n--- Time: %s\n>>> Request: %s\n<<< Reponse Headers:\n%s\nResponse Body:\n%s\n" % (time.strftime("%a, %d %b %Y %H:%M:%S"), url, "\n".join(headers), body))
	file.close()

	# send password via sms to requester
	if code == "200":
		parsed = json.loads(body)
		form = cgi.FieldStorage()
		cc = form.getfirst("cc")
		number = form.getfirst("in")

		if parsed.has_key('pw') and parsed.has_key('login'):
			send_sms(parsed['login'], parsed['pw'])

	ch.close()

if __name__ == "__main__":
    main()
