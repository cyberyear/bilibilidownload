[CmdletBinding()]
param(
    [int]$RefreshMilliseconds = 250
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms

Add-Type @"
using System;
using System.Runtime.InteropServices;

public static class NativePoint {
    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT lpPoint);

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowText(IntPtr hWnd, System.Text.StringBuilder text, int count);

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }
}
"@

function Get-MousePoint {
    $point = New-Object NativePoint+POINT
    [NativePoint]::GetCursorPos([ref]$point) | Out-Null
    return $point
}

function Get-ActiveWindowTitle {
    $handle = [NativePoint]::GetForegroundWindow()
    $builder = New-Object System.Text.StringBuilder 512
    [NativePoint]::GetWindowText($handle, $builder, $builder.Capacity) | Out-Null
    return $builder.ToString()
}

Write-Host "把鼠标移动到目标位置后按 Ctrl+C 结束。"
Write-Host "建议分别记录：搜索框、第一条结果、开始游戏按钮。"

while ($true) {
    $point = Get-MousePoint
    $title = Get-ActiveWindowTitle
    Write-Host ("`rX={0} Y={1}  ActiveWindow={2}   " -f $point.X, $point.Y, $title) -NoNewline
    Start-Sleep -Milliseconds $RefreshMilliseconds
}
