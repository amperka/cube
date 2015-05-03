# -*- coding: utf-8; -*-

import wx
import imaplib
import socket

from time import sleep
from wx.lib.newevent import NewEvent

StatusChangedEvent, EVT_STATUS_CHANGED = NewEvent()

class Mode(object):
    def __init__(self):
        self._evt_transport = wx.Frame(wx.GetApp().GetTopWindow())

    def bind(self, evt, handler):
        self._evt_transport.Bind(evt, handler)

    def unbind(self, evt, handler):
        self._evt_transport.Unbind(evt, handler=handler)

    def _post_event(self, event):
        if isinstance(self._evt_transport, wx.EvtHandler):
            wx.PostEvent(self._evt_transport, event)


class ImapMode(Mode):
    def __init__(self, device, interval=20):
        super(ImapMode, self).__init__()
        self.device = device
        self.interval = interval
        self.status = u''
        self._prev_count = 0
        self._host = None
        self._port = None
        self._login = None
        self._password = None

    def set_host_port(self, host, port):
        self._host = host
        self._port = port

    def set_credentials(self, login, password):
        self._login = login
        self._password = password

    def loop(self):
        self._stopped = False
        while not self._stopped:
            self.set_status(u"Проверка почты…")
            count = 0

            try:
                count = self._fetch_unread_count()
                message = u"Писем: {}".format(count)
            except imaplib.IMAP4.error as e:
                message = u"Неверные логин/пароль"
            except socket.error:
                message = u"Нет соединения с сервером"

            self.set_status(message)

            if self._stopped:
                break

            if count > self._prev_count:
                self.device.blink()

            if count:
                self.device.go_green()
            else:
                self.device.go_red()

            self._prev_count = count

            countdown = self.interval
            while countdown > 0 and not self._stopped:
                sleep(0.1)
                countdown -= 0.1
                self.set_status(u"{} ~ {:.0f}".format(message, countdown))

    def stop(self):
        self._stopped = True

    def set_status(self, status):
        self.status = status
        self._post_event(StatusChangedEvent(status=status))

    def _fetch_unread_count(self):
        connection = imaplib.IMAP4_SSL(self._host, self._port)
        connection.login(self._login, self._password)
        connection.select()
        resp = connection.search(None, 'UnSeen')
        return len(resp[1][0].split())


class GMailMode(ImapMode):
    def __init__(self, device, interval=20):
        super(GMailMode, self).__init__(device, interval)
        self.set_host_port('imap.gmail.com', '993')


class MailruMode(ImapMode):
    def __init__(self, device, interval=20):
        super(MailruMode, self).__init__(device, interval)
        self.set_host_port('imap.mail.ru', '993')
