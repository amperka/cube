# -*- coding: utf-8; -*-

class CubeDevice(object):
    def discover(self):
        import time
        time.sleep(2)
        return [
            '/dev/ttyACM0',
            '/dev/ttyACM1',
        ]

    def go_red(self):
        pass

    def go_green(self):
        pass

    def blink(self):
        pass

    def connect(self, port):
        pass
