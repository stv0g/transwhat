class Deferred(object):
	"""
	Represents a delayed computation. This is a more elegant way to deal with
	callbacks.

	A Deferred object can be thought of as a computation whose value is yet to
	be determined. We can manipulate the Deferred as if it where a regular
	value by using the then method. Computations dependent on the Deferred will
	only proceed when the run method is called.

	Attributes of a Deferred can be accessed directly as methods.

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

class DeferredHasValue(Exception):
	def __init__(self, string):
		super(DeferredHasValue, self).__init__(string)
