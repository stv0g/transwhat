#!/usr/bin/python

__author__ = "Steffen Vogel"
__copyright__ = "Copyright 2013, Steffen Vogel"
__license__ = "GPLv3"
__maintainer__ = "Steffen Vogel"
__email__ = "post@steffenvogel.de"
__status__ = "Prototype"

"""
 This file is part of transWhat

 transWhat is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, either version 3 of the License, or
 any later version.

 transwhat is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with transWhat. If not, see <http://www.gnu.org/licenses/>.
"""

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
