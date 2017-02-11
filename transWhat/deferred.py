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

from functools import partial

class Deferred(object):
	"""
	Represents a delayed computation. This is a more elegant way to deal with
	callbacks.

	A Deferred object can be thought of as a computation whose value is yet to
	be determined. We can manipulate the Deferred as if it where a regular
	value by using the then method. Computations dependent on the Deferred will
	only proceed when the run method is called.

	Attributes of a Deferred can be accessed directly as methods. The result of
	calling these functions will be Deferred.

	Example:
		image = Deferred()
		getImageWithCallback(image.run)
		image.then(displayFunc)

		colors = Deferred()
		colors.append('blue')
		colors.then(print)
		colors.run(['red', 'green']) #=> ['red', 'green', 'blue']
	"""

	def __init__(self):
		self.subscribers = []
		self.computed = False
		self.args = None
		self.kwargs = None

	def run(self, *args, **kwargs):
		"""
		Give a value to the deferred. Calling this method more than once will
		result in a DeferredHasValue exception to be raised.
		"""
		if self.computed:
			raise DeferredHasValue("Deferred object already has a value.")
		else:
			self.args = args
			self.kwargs = kwargs
			for func, deferred in self.subscribers:
				deferred.run(func(*args, **kwargs))
			self.computed = True

	def then(self, func):
		"""
		Apply func to Deferred value. Returns a Deferred whose value will be
		the result of applying func.
		"""
		result = Deferred()
		if self.computed:
			result.run(func(*self.args, **self.kwargs))
		else:
			self.subscribers.append((func, result))
		return result

	def arg(self, n):
		"""
		Returns the nth positional argument of a deferred as a deferred

		Args:
			n - the index of the positional argument
		"""
		def helper(*args, **kwargs):
			return args[n]
		return self.then(helper)

	def when(self, func, *args, **kwargs):
		""" Calls when func(*args, **kwargs) when deferred gets a value """
		def helper(*args2, **kwargs2):
			func(*args, **kwargs)
		return self.then(helper)

	def __getattr__(self, method_name):
		return getattr(Then(self), method_name)


class Then(object):
	"""
	Allows you to call methods on a Deferred.

	Example:
	colors = Deferred()
	Then(colors).append('blue')
	colors.run(['red', 'green'])
	colors.then(print) #=> ['red', 'green', 'blue']
	"""
	def __init__(self, deferred):
		self.deferred = deferred

	def __getattr__(self, name):
		def tryCall(obj, *args, **kwargs):
			if callable(obj):
				return obj(*args, **kwargs)
			else:
				return obj
		def helper(*args, **kwargs):
			func = (lambda x: tryCall(getattr(x, name), *args, **kwargs))
			return self.deferred.then(func)
		return helper

def call(func, *args, **kwargs):
	"""
	Call a function with deferred arguments

	Example:
		colors = Deferred()
		colors.append('blue')
		colors.run(['red', 'green'])
		call(print, colors) #=> ['red', 'green', 'blue']
		call(print, 'hi', colors) #=> hi ['red', 'green', 'blue']
	"""
	for i, c in enumerate(args):
		if isinstance(c, Deferred):
			# Function without deferred arguments
			normalfunc = partial(func, *args[:i])
			# Function with deferred and possibly deferred arguments
			def restfunc(*arg2, **kwarg2):
				apply_deferred = partial(normalfunc, *arg2, **kwarg2)
				return call(apply_deferred, *args[i + 1:], **kwargs)
			return c.then(restfunc)
	items = kwargs.items()
	for i, (k, v) in enumerate(items):
		if isinstance(v, Deferred):
			# Function without deferred arguments
			normalfunc = partial(func, *args, **dict(items[:i]))
			# Function with deferred and possibly deferred arguments
			def restfunc2(*arg2, **kwarg2):
				apply_deferred = partial(normalfunc, *arg2, **kwarg2)
				return call(apply_deferred, **dict(items[i + 1:]))
			return v.then(restfunc2)
	# No items deferred
	return func(*args, **kwargs)

class DeferredHasValue(Exception):
	def __init__(self, string):
		super(DeferredHasValue, self).__init__(string)
