import asyncore, socket

class IOChannel(asyncore.dispatcher):
	def __init__(self, host, port, callback):
		asyncore.dispatcher.__init__(self)

		self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
		self.connect((host, port))

		self.callback = callback
		self.buffer = ""

	def sendData(self, data):
		self.buffer += data

	def handle_connect(self):
		pass

	def handle_close(self):
		self.close()

	def handle_read(self):
		data = self.recv(65536)
		self.callback(data)

	def handle_write(self):
		sent = self.send(self.buffer)
		self.buffer = self.buffer[sent:]

	def writable(self):
		return (len(self.buffer) > 0)

	def readable(self):
		return True
