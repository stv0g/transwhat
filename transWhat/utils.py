# use unicode encoding for all literals by default (for python2.x)
from __future__ import unicode_literals

__author__ = "Steffen Vogel"
__copyright__ = "Copyright 2015-2017, Steffen Vogel"
__license__ = "GPLv3"
__maintainer__ = "Steffen Vogel"
__email__ = "post@steffenvogel.de"

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

import e4u
import base64
import hashlib


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
	return e4u.translate(message.encode("utf-8"), reverse=False, **e4u.SOFTBANK_TRANSLATE_PROFILE)

def decodePassword(password):
	return base64.b64decode(bytes(password))

def sha1hash(data):
	return hashlib.sha1(data).hexdigest()
