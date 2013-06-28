import time


def get_token(number, timeout = 30):
	file = open('tokens')
	file.seek(-1, 2)

	count = 0
	while count < timeout:
		line = file.readline()

		if line in  ["", "\n"]:
			time.sleep(1)
			count += 1
			continue
		else:
			t, n, tk = line[:-1].split("\t")

			if (n == number):
				file.close()
				return tk

	file.close()


print get_token("4917696978528")
