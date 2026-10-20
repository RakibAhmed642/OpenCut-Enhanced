Set oWS = CreateObject("WScript.Shell")
strPath = Replace(WScript.ScriptFullName, WScript.ScriptName, "")
oWS.CurrentDirectory = strPath
' Run Start-OpenCut.bat with standard console window (1)
oWS.Run Chr(34) & strPath & "Start-OpenCut.bat" & Chr(34), 1, False
