import threading
import inspect
import re
import urllib
import time
import os


class Bot:
    def __init__(self, session, name="Bot"):
        self.session = session
        self.name = name

        self.commands = {
            "help": self._help,
            "groups": self._groups,
            "getgroups": self._getgroups,
        }

    def parse(self, message):
        args = message.strip().split(" ")
        cmd = args.pop(0)

        if len(cmd) > 0 and cmd[0] == "\\":
            try:
                self.call(cmd[1:], args)
            except KeyError:
                self.send("invalid command")
            except TypeError:
                self.send("invalid syntax")
        else:
            self.send("a valid command starts with a backslash")

    def call(self, cmd, args=[]):
        func = self.commands[cmd.lower()]
        spec = inspect.getargspec(func)
        maxs = len(spec.args) - 1
        reqs = maxs - len(spec.defaults or [])
        if (reqs > len(args)) or (len(args) > maxs):
            raise TypeError()

        thread = threading.Thread(target=func, args=tuple(args))
        thread.start()

    def send(self, message):
        self.session.backend.handleMessage(self.session.user, self.name, message)

    # commands
    def _help(self):
        self.send(
            """following bot commands are available:
\\help            show this message

following user commands are available:
\\lastseen        request last online timestamp from buddy

following group commands are available
\\leave            permanently leave group chat
\\groups        print all attended groups
\\getgroups        get current groups from WA"""
        )

    def _groups(self):
        for group in self.session.groups:
            buddy = self.session.groups[group].owner
            try:
                nick = self.session.buddies[buddy].nick
            except KeyError:
                nick = buddy

            self.send(
                self.session.groups[group].id
                + "@"
                + self.session.backend.spectrum_jid
                + " "
                + self.session.groups[group].subject
                + " Owner: "
                + nick
            )

    def _getgroups(self):
        # self.session.call("group_getGroups", ("participating",))
        self.session.requestGroupsList(self.session._updateGroups)
