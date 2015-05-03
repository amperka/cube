# -*- coding: utf-8; -*-

from time import sleep
from pyfirmata import Arduino, OUTPUT

class CubeDevice(object):
    def discover(self):
        return [
            '/dev/ttyACM0',
            '/dev/ttyACM1',
        ]

    def go_green(self):
        self.board.digital[5].write(1)
        self.board.digital[8].write(0)
        self.board.digital[6].write(0)
        self.board.digital[9].write(1)

    def go_red(self):
        self.board.digital[5].write(0)
        self.board.digital[8].write(1)
        self.board.digital[6].write(1)
        self.board.digital[9].write(0)

    def blink(self):
        for i in xrange(5):
            self.go_red()
            sleep(0.1)
            self.go_green()
            sleep(0.1)

    def connect(self, port):
        self.board = Arduino(port)
        self.board.digital[5].mode = OUTPUT
        self.board.digital[8].mode = OUTPUT
        self.board.digital[6].mode = OUTPUT
        self.board.digital[9].mode = OUTPUT
