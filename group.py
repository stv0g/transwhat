
class Group():

	def __init__(self, id, owner, subject, subjectOwner):
		self.id = id
		self.subject = subject
		self.subjectOwner = subjectOwner
		self.owner = owner

		self.nick = "me"
		self.participants = { }
