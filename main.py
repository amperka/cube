# -*- coding: utf-8; -*-

import threading
import wx

from device import CubeDevice


class CubeApp(wx.App):
    def __init__(self):
        super(CubeApp, self).__init__()
        self.device = CubeDevice()

    def Run(self):
        frame = MainFrame(None, self.device)
        frame.Show()
        self.MainLoop()



class ManualControlPanel(wx.Panel):
    def __init__(self, parent, device):
        super(ManualControlPanel, self).__init__(parent)
        self.device = device
        self.InitUI()

    def InitUI(self):
        self.red_button = wx.Button(self, label=u'Красный')
        self.green_button = wx.Button(self, label=u'Зелёный')

        self.red_button.Bind(wx.EVT_BUTTON, self.OnRedButton)
        self.green_button.Bind(wx.EVT_BUTTON, self.OnGreenButton)

        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(self.red_button, 1, wx.EXPAND | wx.ALL, 10)
        box.Add(self.green_button, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(box)

    def OnRedButton(self, event):
        self.device.go_red()

    def OnGreenButton(self, event):
        self.device.go_green()


class DiscoveryPanel(wx.Panel):
    def __init__(self, parent):
        super(DiscoveryPanel, self).__init__(parent)
        self.InitUI()

    def InitUI(self):
        label = wx.StaticText(self, label=u'Поиск куба…')
        box = wx.BoxSizer(wx.HORIZONTAL)
        box.Add(label, 1, wx.EXPAND | wx.ALL, 10)
        self.SetSizer(box)

EVT_DISCOVERED = wx.NewId()

class DiscoveryCompletedEvent(wx.PyEvent):
    def __init__(self, ports):
        super(DiscoveryCompletedEvent, self).__init__()
        self.SetEventType(EVT_DISCOVERED)
        self.ports = ports


class MainFrame(wx.Frame):
    def __init__(self, parent, device):
        super(MainFrame, self).__init__(
            parent, title=u'Технокуб', size=(320, 240))
            
        self.device = device
        self.panels = {}
        self.active_panel = None

        self.InitUI()
        self.Centre()
        self.Show()     
        self.Discover()
        
    def InitUI(self):
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.AddPanel('discovery', DiscoveryPanel(self))
        self.AddPanel('manual_control', ManualControlPanel(self, self.device))
        self.ShowPanel('discovery')

        self.SetSizer(self.sizer)

    def AddPanel(self, name, panel):
        self.panels[name] = panel
        panel.Hide()
        self.sizer.Add(panel, 1, wx.EXPAND)

    def ShowPanel(self, name):
        if self.active_panel:
            self.active_panel.Hide()
        self.panels[name].Show()
        self.active_panel = self.panels[name]
        self.Layout()

    def Discover(self):
        self.Connect(-1, -1, EVT_DISCOVERED, self.OnDiscovered)
        threading.Thread(target=self._DoDiscover).start()

    def _DoDiscover(self):
        ports = self.device.discover()
        wx.PostEvent(self, DiscoveryCompletedEvent(ports))

    def OnDiscovered(self, event):
        ports = event.ports
        self.ShowPanel('manual_control')



if __name__ == '__main__':
    CubeApp().Run()
