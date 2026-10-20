Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strPath = fso.GetParentFolderName(WScript.ScriptFullName)
strExe = strPath & "\server\OpenCut-Server.exe"
strPy = "C:\Python313\python.exe"
strSoundService = strPath & "\server\sound_designer_service.py"

' Verify the server exe exists before trying to launch it.
If Not fso.FileExists(strExe) Then
    MsgBox "OpenCut server executable not found:" & vbCrLf & vbCrLf & strExe & vbCrLf & vbCrLf & _
           "The OpenCut installation appears to be missing or corrupt. Please reinstall.", _
           vbCritical + vbOKOnly, "OpenCut"
    WScript.Quit 1
End If

' Add bundled ffmpeg to PATH if present
Dim objEnv
Set objEnv = WshShell.Environment("Process")
objEnv("PYTHONNOUSERSITE") = "0"
If fso.FolderExists(strPath & "\ffmpeg") Then
    objEnv("PATH") = strPath & "\ffmpeg;" & objEnv("PATH")
ElseIf fso.FolderExists(strPath & "\server\ffmpeg") Then
    objEnv("PATH") = strPath & "\server\ffmpeg;" & objEnv("PATH")
End If

' Launch OpenCut AI Studio & Sound Designer Service on port 5682 (hidden)
If fso.FileExists(strPy) And fso.FileExists(strSoundService) Then
    WshShell.Run """" & strPy & """ """ & strSoundService & """", 0, False
End If

' Launch OpenCut Core Server on port 5679 (hidden)
WshShell.Run """" & strExe & """", 0, False
