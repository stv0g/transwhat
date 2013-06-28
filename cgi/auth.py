#!/usr/bin/python

import os
import sys
import cgi
import cgitb
import time

sys.path.insert(1, os.path.join(sys.path[0], '..'))

from constants import *

def cookies(str):
	return dict(c.split('=') for c in str.split(";"))

def save_token(timestamp, number, token, filename="tokens"):
	file = open(filename, 'a')
	file.write("%s\t%s\t%s\n" % (str(timestamp), number, token))
	file.close()

def main():
	form = cgi.FieldStorage()
	number = form.getfirst("number")
	auth_url = form.getfirst("auth_url")
	token = form.getfirst("code")

	if auth_url:
		print "Status: 301 Moved"
		print "Location: %s" % auth_url
		print "Content-type: text/html"
		print "Set-Cookie: number=%s" % number
		print "\n\n";

	elif token and os.environ.has_key('HTTP_COOKIE'):
		print "Status: 301 Moved"
		print "Content-type: text/html"
		print "Location: http://whatsapp.0l.de"
		print

		c = cookies(os.environ['HTTP_COOKIE'])
		save_token(time.time(), c['number'], token, TOKEN_FILE)

	else:
		print "Content-type: text/html"
		print "\n"
		print "something strange happened :("

if __name__ == "__main__":
    main()
