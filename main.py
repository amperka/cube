# -*- coding: utf-8; -*-

import platform
import threading
import wx
import modes
import icons

from wx.lib.newevent import NewEvent
from device import CubeDevice


#==============================================================================
class CubeApp(wx.App):
    def __init__(self):
        super(CubeApp, self).__init__()
        self.device = CubeDevice()

    def Run(self):
        frame = MainFrame(None, self.device)
        frame.Show()
        self.SetTopWindow(frame)
        self.SetExitOnFrameDelete(True)
        TaskBarIcon()
        self.MainLoop()
        self.device.disconnect()

#==============================================================================

class TaskBarIcon(wx.TaskBarIcon):
    def __init__(self):
        super(TaskBarIcon, self).__init__()
        self.SetupIcon()
        self.Bind(wx.EVT_TASKBAR_LEFT_DOWN, self.OnLeftClick)

    def CreatePopupMenu(self):
        menu = wx.Menu()
        exit = wx.MenuItem(menu, -1, u'Закрыть')
        menu.Bind(wx.EVT_MENU, self.OnExit, id=item.GetId())
        menu.AppendItem(exit)
        return menu

    def SetupIcon(self):
        img = icons.icon_16
        self.SetIcon(icons.icon_16.GetIcon(), u"Куб")

    def OnLeftClick(self, event):
        wx.GetApp().GetTopWindow().Show()

    def OnExit(self, event):
        wx.GetApp().GetTopWindow().Close()

#==============================================================================
class ActionPanel(wx.Panel):
    def __init__(self, parent, device):
        super(ActionPanel, self).__init__(parent)
        self.device = device
        self.panels = {}
        self.active_panel = None
        self.InitUI()

    def InitUI(self):
        self.mode_combobox = wx.ComboBox(self, style=wx.CB_READONLY)
        self.mode_combobox.Bind(wx.EVT_COMBOBOX, self.OnComboboxChanged)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.mode_combobox, 0, wx.EXPAND | wx.ALL, 10)

        self.AddMode(u'Управлять вручную', ManualControlPanel(self, self.device))

        gmail_mode = modes.GMailMode(self.device)
        self.AddMode(u'Проверять GMail', MailPanel(self, gmail_mode, False))

        mailru_mode = modes.MailruMode(self.device)
        self.AddMode(u'Проверять Mail.ru', MailPanel(self, mailru_mode, False))

        generic_imap_mode = modes.ImapMode(self.device)
        self.AddMode(u'Проверять почту через IMAP', MailPanel(self, generic_imap_mode, True))

        self.ShowPanel(u'Управлять вручную')
        self.SetSizer(self.sizer)

    def AddMode(self, name, panel):
        self.panels[name] = panel
        self.mode_combobox.Append(name)
        panel.Hide()
        self.sizer.Add(panel, 1, wx.EXPAND | wx.ALL, 10)

    def ShowPanel(self, name):
        if self.active_panel:
            self.active_panel.DeactivateMode()
            self.active_panel.Hide()
        self.panels[name].Show()
        self.active_panel = self.panels[name]
        self.active_panel.ActivateMode()
        self.mode_combobox.SetSelection(self.mode_combobox.FindString(name))
        self.Layout()

    def OnComboboxChanged(self, event):
        self.ShowPanel(self.mode_combobox.GetValue())


#==============================================================================
class MailPanel(wx.Panel):
    def __init__(self, parent, mode, show_imap_host_port):
        super(MailPanel, self).__init__(parent)
        self.mode = mode
        self.show_imap_host_port = show_imap_host_port

        self.InitUI()
        self.Bind(wx.EVT_WINDOW_DESTROY, lambda e: self.mode.stop())

    def InitUI(self):
        sizer = wx.BoxSizer(wx.VERTICAL)

        credentials_panel = self.CreateCredentialsUI()
        self.run_button = wx.Button(self, label=u'Поехали!')
        self.cancel_button = wx.Button(self, label=u'Остановить')
        self.status_label = wx.StaticText(self)

        self.run_button.Bind(wx.EVT_BUTTON, self.OnRunButton)
        self.cancel_button.Bind(wx.EVT_BUTTON, self.OnCancelButton)

        sizer.Add(credentials_panel, 1, wx.EXPAND)
        sizer.Add(self.status_label, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.run_button, 0, wx.EXPAND | wx.ALL, 10)
        sizer.Add(self.cancel_button, 0, wx.EXPAND | wx.ALL, 10)
        self.cancel_button.Hide()

        self.SetSizer(sizer)

    def CreateCredentialsUI(self):
        cp = wx.Panel(self)

        sizer = wx.FlexGridSizer(rows=0, cols=2, vgap=10, hgap=10)
        sizer.AddGrowableCol(1, 1)

        if self.show_imap_host_port:
            self.host_input = wx.TextCtrl(cp)
            self.port_input = wx.TextCtrl(cp)
            sizer.AddMany([
                wx.StaticText(cp, label=u"Хост"),
                (self.host_input, 1, wx.EXPAND),

                wx.StaticText(cp, label=u"Порт"),
                (self.port_input, 1, wx.EXPAND),
            ])

        self.login_input = wx.TextCtrl(cp)
        self.password_input = wx.TextCtrl(cp, style=wx.TE_PASSWORD)
        sizer.AddMany([
            wx.StaticText(cp, label=u"Логин"),
            (self.login_input, 1, wx.EXPAND),

            wx.StaticText(cp, label=u"Пароль"),
            (self.password_input, 1, wx.EXPAND),
        ])

        cp.SetSizer(sizer)

        return cp

    def ActivateMode(self):
        if self.show_imap_host_port:
            self.host_input.Enable()
            self.port_input.Enable()

        self.login_input.Enable()
        self.password_input.Enable()
        self.run_button.Show()
        self.cancel_button.Hide()
        self.status_label.SetLabel(u'')

    def DeactivateMode(self):
        self.mode.stop()

    def OnRunButton(self, event):
        if self.show_imap_host_port:
            self.mode.set_host_port(self.host_input.GetValue(),
                                    self.port_input.GetValue())

        self.mode.set_credentials(self.login_input.GetValue(),
                                  self.password_input.GetValue())

        if self.show_imap_host_port:
            self.host_input.Disable()
            self.port_input.Disable()

        self.login_input.Disable()
        self.password_input.Disable()
        self.run_button.Hide()
        self.cancel_button.Show()
        self.Layout()

        self.mode.bind(modes.EVT_STATUS_CHANGED, self.OnStatusChanged)
        threading.Thread(target=self.mode.loop).start()

    def OnCancelButton(self, event):
        self.DeactivateMode()
        self.ActivateMode()
        self.mode.unbind(modes.EVT_STATUS_CHANGED, self.OnStatusChanged)
        self.Layout()

    def OnStatusChanged(self, event):
        self.status_label.SetLabel(event.status)


#==============================================================================
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

    def ActivateMode(self):
        pass

    def DeactivateMode(self):
        pass


#==============================================================================
class LongTaskPanel(wx.Panel):
    def __init__(self, parent, text):
        super(LongTaskPanel, self).__init__(parent)
        self.InitUI(text)

    def InitUI(self, text):
        panel = wx.Panel(self)
        label = wx.StaticText(
            panel, label=text,
            style=wx.ALIGN_CENTRE_HORIZONTAL)

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)

        hbox.Add(label, 1, wx.ALIGN_CENTRE_VERTICAL, 10)
        vbox.Add(panel, 1, wx.ALIGN_CENTRE_HORIZONTAL, 10)

        panel.SetSizer(hbox)
        self.SetSizer(vbox)

#==============================================================================
PortSelectedEvent, EVT_PORT_SELECTED = NewEvent()

class PortSelectionPanel(wx.Panel):
    def __init__(self, parent, device):
        super(PortSelectionPanel, self).__init__(parent)
        self.device = device
        self.InitUI()

    def InitUI(self):
        box = wx.BoxSizer(wx.VERTICAL)
        self.listbox = wx.ListBox(self)
        ok_button = wx.Button(self, label=u'OK')
        ok_button.Bind(wx.EVT_BUTTON, self.OnOK)

        box.Add(wx.StaticText(self, label=u'К какому порту подключен куб?'), 0, wx.EXPAND | wx.ALL, 10)
        box.Add(self.listbox, 1, wx.EXPAND | wx.ALL, 10)
        box.Add(ok_button, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(box)

    def SetPorts(self, ports):
        self.listbox.InsertItems(ports, 0)

    def OnOK(self, event):
        # TODO: what if nothing selected?
        port = self.listbox.GetString(self.listbox.GetSelection())
        wx.PostEvent(self, PortSelectedEvent(port=port))


#==============================================================================
SearchAgainEvent, EVT_SEARCH_AGAIN = NewEvent()

class PortNotFoundPanel(wx.Panel):
    def __init__(self, parent):
        super(PortNotFoundPanel, self).__init__(parent)
        self.InitUI()

    def InitUI(self):
        vbox = wx.BoxSizer(wx.VERTICAL)

        search_again_button = wx.Button(self, label=u'Искать снова')
        search_again_button.Bind(wx.EVT_BUTTON, lambda e: wx.PostEvent(self, SearchAgainEvent()))

        txt_box = wx.BoxSizer(wx.HORIZONTAL)
        txt_panel = wx.Panel(self)
        txt = wx.StaticText(
            txt_panel, label=u'Куб не найден.\nУбедитесь, что он подключён к компьютеру.',
            style=wx.ALIGN_CENTRE_HORIZONTAL | wx.TE_MULTILINE)
        txt_box.Add(txt, 1, wx.ALIGN_CENTRE_VERTICAL, 10)
        txt_panel.SetSizer(txt_box)

        vbox.Add(txt_panel, 1, wx.ALIGN_CENTRE_HORIZONTAL, 10)
        vbox.Add(search_again_button, 0, wx.EXPAND | wx.ALL, 10)

        self.SetSizer(vbox)


#==============================================================================
DiscoveredEvent, EVT_DISCOVERED = NewEvent()
ConnectedEvent, EVT_CONNECTED = NewEvent()

class MainFrame(wx.Frame):
    def __init__(self, parent, device):
        super(MainFrame, self).__init__(
            parent, title=u'Технокуб', size=(320, 360))
            
        self.device = device
        self.active_panel = None

        self.InitUI()
        self.Centre()
        self.Show()     
        self.Discover()
        
    def InitUI(self):
        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.discovery_panel = self.AddPanel(LongTaskPanel(self, u'Поиск куба…'))
        self.connection_panel = self.AddPanel(LongTaskPanel(self, u'Подключение к кубу…'))
        self.port_selection_panel = self.AddPanel(PortSelectionPanel(self, self.device))
        self.port_not_found_panel = self.AddPanel(PortNotFoundPanel(self))
        self.action_panel = self.AddPanel(ActionPanel(self, self.device))

        self.port_selection_panel.Bind(EVT_PORT_SELECTED, self.OnPortSelected)
        self.port_not_found_panel.Bind(EVT_SEARCH_AGAIN, self.OnSearchAgain)
        self.Bind(EVT_DISCOVERED, self.OnDiscovered)
        self.Bind(EVT_CONNECTED, self.OnConnected)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        self.SetSizer(self.sizer)

        self.SetIcon(icons.icon_32.GetIcon())

    def AddPanel(self, panel):
        panel.Hide()
        self.sizer.Add(panel, 1, wx.EXPAND)
        return panel

    def ShowPanel(self, panel):
        if self.active_panel:
            self.active_panel.Hide()
        panel.Show()
        self.active_panel = panel
        self.Layout()

    def Discover(self):
        self.ShowPanel(self.discovery_panel)
        threading.Thread(target=self._DoDiscover).start()

    def _DoDiscover(self):
        ports = self.device.discover()
        wx.PostEvent(self, DiscoveredEvent(ports=ports))

    def OnDiscovered(self, event):
        ports = event.ports
        if len(ports) > 1:
            self.port_selection_panel.SetPorts(ports)
            self.ShowPanel(self.port_selection_panel)
        elif len(ports) == 1:
            self.ConnectDevice(ports[0])
        else:
            self.ShowPanel(self.port_not_found_panel)

    def OnPortSelected(self, event):
        self.ConnectDevice(event.port)

    def OnSearchAgain(self, event):
        self.ShowPanel(self.discovery_panel)
        self.Discover()

    def ConnectDevice(self, port):
        self.ShowPanel(self.connection_panel)
        threading.Thread(target=self._DoConnectDevice, args=(port, )).start()
    
    def _DoConnectDevice(self, port):
        self.device.connect(port)
        wx.PostEvent(self, ConnectedEvent())

    def OnConnected(self, event):
        self.ShowPanel(self.action_panel)

    def OnClose(self, event):
        if platform.system() == 'Windows':
            self.Iconize()
        else:
            self.Destroy()



if __name__ == '__main__':
    CubeApp().Run()
