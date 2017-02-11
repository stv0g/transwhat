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

import Queue
import threading

# This queue is for other threads that want to execute code in the main thread
eventQueue = Queue.Queue()

def runInThread(threadFunc, callback):
	"""
	Executes threadFunc in a new thread. The result of threadFunc will be
	pass as the first argument to callback. callback will be called in the main
	thread.
	"""
	def helper():
		# Execute threadfunc in new thread
		result = threadFunc()
		# Queue callback to be call in main thread
		eventQueue.put(lambda: callback(result))
	thread = threading.Thread(target=helper)
	thread.start()
