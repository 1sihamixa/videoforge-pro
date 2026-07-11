Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\autosystem"
WshShell.Run "python app.py", 0, False
