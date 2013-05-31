
class Group():

	def __init__(self, id, subject, owner):
		self.id = id
		self.subject = subject
		self.owner = owner
		self.participants = { }
