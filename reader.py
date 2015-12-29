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

import time

def get_token(number, timeout = 30):
	file = open(u'tokens')
	file.seek(-1, 2)

	count = 0
	while count < timeout:
		line = file.readline()

		if line in  [u"", u"\n"]:
			time.sleep(1)
			count += 1
			continue
		else:
			t, n, tk = line[:-1].split(u"\t")

			if (n == number):
				file.close()
				return tk

	file.close()


print get_token(u"4917696978528")
