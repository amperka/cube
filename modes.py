# -*- coding: utf-8; -*-

import wx
import imaplib
import socket
import urllib2
import json
import threading
import logging

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


class SlackMode(ImapMode):
    def __init__(self, device, interval=10):
        self.UNREADS = []
        self._init_logging()
        return super(SlackMode, self).__init__(device, interval)

    def _init_logging(self):
        logger = logging.getLogger(SlackMode.__name__)
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - '
                                      '%(message)s')
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        self._logger = logger

    def decorate(func):
        base_url = 'https://slack.com/api/'

        def wrapper(self, uri_part):
            uri_part = func(self, uri_part)
            token = self._login
            return '%s%s?token=%s' % (base_url, uri_part, token)
        return wrapper

    @decorate
    def get_url(self, uri_part):
        return uri_part

    def get_unreads_count(self, item_id, uri_part):
        history_url = self.get_url('%s.history' % uri_part)
        url = '%s&channel=%s&unreads=True' % (history_url, item_id)
        try:
            history = json.loads(urllib2.urlopen(url).read())
            self.UNREADS.append(history['unread_count_display'])
        except urllib2.URLError, e:
            self.error(e)

    def get_unreads(self, uri, key):
        url = self.get_url(uri)
        resp = json.loads(urllib2.urlopen(url).read())
        if 'error' in resp:
            self.error(str(resp['error']))

        items = resp[key]
        ids = map(lambda x: x['id'], items)
        threads = []
        for item_id in ids:
            uri_part = uri.split('.')[0]
            t = threading.Thread(target=self.get_unreads_count,
                                 args=(item_id, uri_part))
            threads.append(t)
        map(lambda x: x.start(), threads)
        map(lambda x: x.join(), threads)

    def _fetch_threads(self):
        self.get_unreads('channels.list', 'channels')
        self.get_unreads('im.list', 'ims')

    def error(self, message):
        self._logger.error('Ошибка: %s', message)
        self.set_status(message)
        self.stop()
        raise LoginError

    def _fetch_unread_count(self):
        self.UNREADS = []
        if not self._login:
            message = 'Отсутствует токен.'
            self.error(message)

        self._fetch_threads()
        res = sum(self.UNREADS)
        if res:
            self._logger.info('Нових писем: %s', res)
        return res


class LoginError(Exception):
    pass
