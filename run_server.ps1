$python = "C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe"
$script = "C:\autosystem\server.py"
Start-Process -NoNewWindow -FilePath $python -ArgumentList $script
Write-Output "Server started with PID: $((Get-Process -Name python | Where-Object { $_.CommandLine -match 'server.py' }).Id)"
