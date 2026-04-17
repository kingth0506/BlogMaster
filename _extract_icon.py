import subprocess
ps = r'''
Add-Type -AssemblyName System.Drawing
$icon = [System.Drawing.Icon]::ExtractAssociatedIcon("C:\Users\kingt\Desktop\NaverBlogAuto_Install.exe")
$icon.ToBitmap().Save("C:\Users\kingt\Desktop\NaverBlogAuto\_installer_icon.png")
Write-Host "OK"
'''
r = subprocess.run(['powershell', '-NoProfile', '-Command', ps], capture_output=True, text=True)
print('stdout:', r.stdout)
print('stderr:', r.stderr)
