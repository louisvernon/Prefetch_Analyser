import sys, os, time
import binascii
import re
import datetime
try:
    import wx
    wximport = True
except:
    wximport = False
    print "wxpython failed to load - reverting to command line."


def analyse_prefetch(filename):
    
    info = {}   
    try:
        prefetch_file = open(filename, "rb")
    except:
        return None,  "Prefetch file not found:" + filename
        
    header = prefetch_file.read(8)

    info["filename"] = filename
    # determine OS 
    if(header == "\x11\x00\x00\x00\x53\x43\x43\x41"):
        #print "OS: WinXP/2003"
        operating_sys = "XP"
    elif(header == "\x17\x00\x00\x00\x53\x43\x43\x41"):
        #print "OS: Win7/Vista"
        operating_sys = "7"
    else:
        return None, "Unknown Prefetch File Type."
    
    info["operating_sys"] = operating_sys
    
    # read executable file name
    prefetch_file.seek(16)
    filename_raw = prefetch_file.read(64)[0::2]
    filename_str = filename_raw.split("\x00")
    info["exec_name"] = filename_str[0]
    
    
    # retrieve file node metadata
    file_info = os.stat(filename)
    info["creation_time"] = time.ctime(file_info[9])
    info["access_time"] = time.ctime(file_info[7])
    info["modified_time"] = time.ctime(file_info[8])
    
    
    # retrieve execution counts
    if(operating_sys=="XP"):
        prefetch_file.seek(144)
    elif(operating_sys=="7"):
        prefetch_file.seek(152)
    
    # retrieve stored execution time:
    run_count_raw = prefetch_file.read(4)[::-1]
    info["run_count"] = int(binascii.hexlify(run_count_raw), 16)
    
    # retrieve execution time
    if(operating_sys=="XP"):
        prefetch_file.seek(120)
    elif(operating_sys=="7"):
        prefetch_file.seek(128)
    
    run_time_hex = binascii.hexlify(prefetch_file.read(8)[::-1])
    # get windows time in seconds and then subtract the number of seconds between windows and unix epoch time
    run_time = (int(run_time_hex,16) / 1E7) - 11644473600
    info["exec_date"] = time.ctime(run_time)
    
    
        
    # retrieve loaded files
    full_binary = (''.join(open(filename, "rb").readlines()))[0::2]
    full_list = full_binary.split("\DEVICE")
    loaded_files = []
    
    for item in full_list:
        if("\n" in item): continue
        bad = re.search("[A-Za-z 0-9\\\.\$_-]+",item)
        fileid = bad.group(0)
        if(fileid.count("\\")<2 or fileid[-1] == "\\"):
            break
        loaded_files.append("\DEVICE" + fileid)
    
    info["loaded_files"] = loaded_files
    

    output_text = "Executable name: " + str(info["exec_name"]) + "\r\n"
    if(info["operating_sys"]=="XP"):
        output_text += "Prefetch file generated on WinXP/2003 \r\n"
    else:
        output_text += "Prefetch file generated on Vista/Win7 \r\n"
    
    output_text += "File was created: " + str(info["creation_time"])  + "\r\n"
    output_text += "File last accessed: " + str(info["access_time"]) + "\r\n"
    output_text += "File last modified: " + str(info["modified_time"]) + "\r\n"
    output_text += "Executable Run: " + str(info["run_count"]) + " times." + "\r\n"
    output_text += "Last Executed: " + str(info["exec_date"]) + "\r\n"
    output_text += "Files loaded by executable:"  + "\r\n"
    for accessed_file in info["loaded_files"]:
        output_text += accessed_file +"\r\n"
        
    
    return info, output_text

    
class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        global panel,menuSave, prefetch_text, prefetch_info, m_text
        wx.Frame.__init__(self, parent, title=title, size=(800,800))
        panel = wx.Panel(self)
        m_text = wx.TextCtrl (panel, 1, style=wx.TE_MULTILINE)
        m_text.SetEditable(False)
        bsizer = wx.BoxSizer()
        bsizer.Add(m_text, 1, wx.EXPAND)
        
        panel.SetSizerAndFit(bsizer)
        
        
        self.CreateStatusBar() # A StatusBar in the bottom of the window
        

        # Setting up the menu.
        filemenu= wx.Menu()

        # wx.ID_ABOUT and wx.ID_EXIT are standard ids provided by wxWidgets.
        menuOpen = filemenu.Append(101, "&Open"," Open Prefetch File")
        menuSave = filemenu.Append(102, "&Save"," Save Prefetch Analysis")
        menuSave.Enable(False)
        filemenu.AppendSeparator()
        menuAbout = filemenu.Append(wx.ID_ABOUT, "&About"," About Prefetch Analyser")
        menuExit = filemenu.Append(wx.ID_EXIT,"&Exit"," Terminate the program")

        # Creating the menubar.
        menuBar = wx.MenuBar()
        menuBar.Append(filemenu,"&File") # Adding the "filemenu" to the MenuBar
        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        # Set events.
        self.Bind(wx.EVT_MENU, self.OnSave, menuSave)
        self.Bind(wx.EVT_MENU, self.OnAbout, menuAbout)
        self.Bind(wx.EVT_MENU, self.OnExit, menuExit)
        self.Bind(wx.EVT_MENU, self.OnOpen, menuOpen)

        self.Show(True)

    def OnAbout(self,e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "Made in a hurry by Louis Vernon (louis.vernon@gmail.com)", "A wxpython prefetch viewer", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.
        
    def OnSave(self, event):
        global prefetch_text, prefetch_info
        now = datetime.datetime.now()
        timestamp = str(now.year) + "-" + str(now.month) + "-" + str(now.day)  + "-" + str(now.hour) + "-" + str(now.minute) + "-" + str(now.second)
        log_file_name = prefetch_info["filename"] + "-" + timestamp + ".log"
        output = open(log_file_name, "w")
        output.write(prefetch_text)
        output.close()
        dlg = wx.MessageDialog( self, "Prefetch info written to: '" + log_file_name +"'", "SAVED", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished

    def OnOpen(self, event):
        global panel,menuSave, prefetch_text, prefetch_info, m_text
        self.dirname = ''
        dlg = wx.FileDialog(self, "Choose a file", self.dirname, "", "*.pf", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            self.filename = dlg.GetFilename()
            self.dirname = dlg.GetDirectory()
            filename = os.path.join(self.dirname, self.filename)
            prefetch_info, prefetch_text = analyse_prefetch(filename)
            m_text.SetLabel(prefetch_text)
            if(prefetch_info == None):
                menuSave.Enable(False)
            else:
                menuSave.Enable(True)
           
        dlg.Destroy()
        
    def OnExit(self,e):
        self.Close(True)  # Close the frame.
if(wximport and len(sys.argv)<2):
    app = wx.App(False)
    frame = MainWindow(None, "Prefetch Analyser")
    app.MainLoop()
else:
    if(len(sys.argv)!=2):
        print "Usage: python Prefetch_Analyser prefetch_file.pf"
        sys.exit()
    else:
        info, text = analyse_prefetch(sys.argv[1])
        print text


