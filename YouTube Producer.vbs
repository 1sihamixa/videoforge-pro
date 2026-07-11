' YouTube Producer Pro v2.0 - انقر نقراً مزدوجاً للتشغيل

Dim fso, shell
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

Dim paths, p
paths = Array("C:\autosystem\youtube_workspace", _
  "C:\autosystem\youtube_workspace\audio", _
  "C:\autosystem\youtube_workspace\videos", _
  "C:\autosystem\youtube_workspace\subtitles", _
  "C:\autosystem\youtube_workspace\thumbnails", _
  "C:\autosystem\youtube_workspace\exports", _
  "C:\autosystem\youtube_workspace\bg_videos", _
  "C:\autosystem\youtube_workspace\music", _
  "C:\autosystem\youtube_workspace\logs")

For Each p In paths
    If Not fso.FolderExists(p) Then
        fso.CreateFolder(p)
    End If
Next

shell.CurrentDirectory = "C:\autosystem"
shell.Run "pythonw.exe -m youtube_producer --gui", 0, False
Set shell = Nothing
Set fso = Nothing
