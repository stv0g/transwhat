
import logging

class Number():

	def __init__(self, number, db):
		self.number = number
		self.db = db

		cur = self.db.cursor()
		cur.execute("SELECT id FROM numbers WHERE number = %s", self.number)
		if (cur.rowcount):
			self.id = cur.fetchone()[0]
			logging.info("sql: found existing number %s (id=%s)", self.number, self.id)
		else:
			cur.execute("INSERT INTO numbers (number) VALUES (%s)", (self.number))
			self.db.commit()
			self.id = cur.lastrowid
			logging.info("sql: added new number %s (id=%s)", self.number, self.id)

	def __str__(self):
		return "%s (id=%s)" % (self.number, self.id)


class Buddy():

	def __init__(self, owner, number, nick, id, db):
		self.owner = owner
		self.number = number
		self.nick = nick
		self.id = id
		self.db = db

	def update(self, nick):
		self.nick = nick
		cur = self.db.cursor()
		cur.execute("UPDATE roster SET nick = %s WHERE owner_id = %s AND buddy_id = %s", (self.nick, self.owner.id, self.number.id))
		self.db.commit()

	def delete(self):
		cur = self.db.cursor()
		cur.execute("DELETE FROM roster WHERE owner_id = %s AND buddy_id = %s", (self.owner.id, self.number.id))
		self.db.commit()
		self.id = None

	@staticmethod
	def create(owner, number, nick, db):
		cur = db.cursor()
		cur.execute("INSERT INTO roster (owner_id, buddy_id, nick) VALUES (%s, %s, %s)", (owner.id, number.id, nick))
		db.commit()
		
		return Buddy(owner, number, nick, cur.lastrowid, db)

	def __str__(self):
		return "%s (nick=%s, id=%s)" % (self.number, self.nick, self.id)

class Roster():

	def __init__(self, owner, db):
		self.db = db
		self.owner = Number(owner, db)
		self.buddies = { }

	def load(self):
		cur = self.db.cursor()
		cur.execute("""SELECT
					r.id AS id,
					nb.number AS number,
					r.nick AS nick
				FROM roster AS r 
				LEFT JOIN numbers AS nb
					ON r.buddy_id = nb.id
				WHERE
					r.owner_id = %s""", self.owner.id)

		for i in range(cur.rowcount):
			id, number, nick, = cur.fetchone()
			buddy = Buddy(self.owner, Number(number, self.db), nick.decode('latin1'), id, self.db)
			self.buddies[number] = buddy
			logging.info("roster load: %s", buddy)

	def add(self, number, nick):
		buddy = Buddy.create(self.owner, Number(number, self.db), nick, self.db)
		self.buddies[number] = buddy
		logging.info("roster add: %s <- %s", self.owner, buddy)

	def remove(self, number):
		logging.info("roster delete: %s", number)
		self.buddies[number].delete()
		del self.buddies[number]
