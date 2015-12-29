__author__ = u"Steffen Vogel"
__copyright__ = u"Copyright 2015, Steffen Vogel"
__license__ = u"GPLv3"
__maintainer__ = u"Steffen Vogel"
__email__ = u"post@steffenvogel.de"

u"""
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

import e4u
import base64
import hashlib

def ago(secs):
	periods = [u"second", u"minute", u"hour", u"day", u"week", u"month", u"year", u"decade"]
	lengths = [60, 60, 24, 7,4.35, 12, 10]

	j = 0
	diff = secs

	while diff >= lengths[j]:
		diff /= lengths[j]
		diff = round(diff)
		j += 1

	period = periods[j]
	if diff > 1: period += u"s"

	return u"%d %s ago" % (diff, period)

def softToUni(message):
	message = message.decode(u"utf-8")
	return e4u.translate(message, reverse=False, **e4u.SOFTBANK_TRANSLATE_PROFILE)

def decodePassword(password):
	return base64.b64decode(bytes(password.encode(u"utf-8")))

def sha1hash(data):
    return hashlib.sha1(data).hexdigest()
