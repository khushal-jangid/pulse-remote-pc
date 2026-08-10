# PowerShell Bridge for PulseRemote PC
# Native Windows API interop for high performance, low-latency control

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;

public class WinAPI {
    [DllImport("user32.dll")]
    public static extern bool SetCursorPos(int x, int y);

    [DllImport("user32.dll")]
    public static extern bool GetCursorPos(out POINT lpPoint);

    [DllImport("user32.dll")]
    public static extern void mouse_event(uint dwFlags, int dx, int dy, uint dwData, UIntPtr dwExtraInfo);

    [DllImport("user32.dll")]
    public static extern void keybd_event(byte bVk, byte bScan, uint dwFlags, UIntPtr dwExtraInfo);

    [DllImport("user32.dll")]
    public static extern short VkKeyScan(char ch);

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT {
        public int X;
        public int Y;
    }

    public const uint MOUSEEVENTF_MOVE      = 0x0001;
    public const uint MOUSEEVENTF_LEFTDOWN  = 0x0002;
    public const uint MOUSEEVENTF_LEFTUP    = 0x0004;
    public const uint MOUSEEVENTF_RIGHTDOWN = 0x0008;
    public const uint MOUSEEVENTF_RIGHTUP   = 0x0010;
    public const uint MOUSEEVENTF_MIDDLEDOWN= 0x0020;
    public const uint MOUSEEVENTF_MIDDLEUP  = 0x0040;
    public const uint MOUSEEVENTF_WHEEL     = 0x0800;
    public const uint MOUSEEVENTF_HWHEEL    = 0x01000;

    public const uint KEYEVENTF_KEYDOWN     = 0x0000;
    public const uint KEYEVENTF_KEYUP       = 0x0002;
    public const uint KEYEVENTF_EXTENDEDKEY = 0x0001;

    // Virtual Keys
    public const byte VK_VOLUME_MUTE = 0xAD;
    public const byte VK_VOLUME_DOWN = 0xAE;
    public const byte VK_VOLUME_UP   = 0xAF;
    public const byte VK_MEDIA_NEXT  = 0xB0;
    public const byte VK_MEDIA_PREV  = 0xB1;
    public const byte VK_MEDIA_STOP  = 0xB2;
    public const byte VK_MEDIA_PLAY  = 0xB3;
    public const byte VK_LWIN        = 0x5B;
    public const byte VK_RETURN      = 0x0D;
    public const byte VK_BACK        = 0x08;
    public const byte VK_TAB         = 0x09;
    public const byte VK_ESCAPE      = 0x1B;
    public const byte VK_SPACE       = 0x20;
    public const byte VK_LEFT        = 0x25;
    public const byte VK_UP          = 0x26;
    public const byte VK_RIGHT       = 0x27;
    public const byte VK_DOWN        = 0x28;
    public const byte VK_CONTROL     = 0x11;
    public const byte VK_SHIFT       = 0x10;
    public const byte VK_MENU        = 0x12; // Alt
}
"@ -ReferencedAssemblies System.Drawing

Add-Type -AssemblyName System.Windows.Forms

[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "READY"

while ($true) {
    $line = [Console]::ReadLine()
    if ($null -eq $line) { break }
    if ($line.Trim() -eq "") { continue }

    try {
        $cmd = $line | ConvertFrom-Json
        $action = $cmd.action

        switch ($action) {
            "move_rel" {
                $pt = New-Object WinAPI+POINT
                [WinAPI]::GetCursorPos([ref]$pt) | Out-Null
                $newX = $pt.X + [int]$cmd.dx
                $newY = $pt.Y + [int]$cmd.dy
                [WinAPI]::SetCursorPos($newX, $newY) | Out-Null
            }
            "move_abs" {
                [WinAPI]::SetCursorPos([int]$cmd.x, [int]$cmd.y) | Out-Null
            }
            "click" {
                $button = $cmd.button
                if ($button -eq "right") {
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, [UIntPtr]::Zero)
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_RIGHTUP, 0, 0, 0, [UIntPtr]::Zero)
                } elseif ($button -eq "middle") {
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, [UIntPtr]::Zero)
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_MIDDLEUP, 0, 0, 0, [UIntPtr]::Zero)
                } else {
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [UIntPtr]::Zero)
                }
            }
            "double_click" {
                [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
                [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [UIntPtr]::Zero)
                Start-Sleep -Milliseconds 50
                [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
                [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [UIntPtr]::Zero)
            }
            "mouse_down" {
                $button = $cmd.button
                if ($button -eq "right") {
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, [UIntPtr]::Zero)
                } else {
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTDOWN, 0, 0, 0, [UIntPtr]::Zero)
                }
            }
            "mouse_up" {
                $button = $cmd.button
                if ($button -eq "right") {
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_RIGHTUP, 0, 0, 0, [UIntPtr]::Zero)
                } else {
                    [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_LEFTUP, 0, 0, 0, [UIntPtr]::Zero)
                }
            }
            "scroll" {
                $dy = [int]$cmd.dy
                [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_WHEEL, 0, 0, [uint32]$dy, [UIntPtr]::Zero)
            }
            "hscroll" {
                $dx = [int]$cmd.dx
                [WinAPI]::mouse_event([WinAPI]::MOUSEEVENTF_HWHEEL, 0, 0, [uint32]$dx, [UIntPtr]::Zero)
            }
            "type" {
                $text = $cmd.text
                if ($text) {
                    [System.Windows.Forms.SendKeys]::SendWait($text)
                }
            }
            "key" {
                $k = $cmd.key
                switch ($k) {
                    "enter"     { [WinAPI]::keybd_event([WinAPI]::VK_RETURN, 0, 0, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_RETURN, 0, 2, [UIntPtr]::Zero) }
                    "backspace" { [WinAPI]::keybd_event([WinAPI]::VK_BACK, 0, 0, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_BACK, 0, 2, [UIntPtr]::Zero) }
                    "tab"       { [WinAPI]::keybd_event([WinAPI]::VK_TAB, 0, 0, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_TAB, 0, 2, [UIntPtr]::Zero) }
                    "esc"       { [WinAPI]::keybd_event([WinAPI]::VK_ESCAPE, 0, 0, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_ESCAPE, 0, 2, [UIntPtr]::Zero) }
                    "space"     { [WinAPI]::keybd_event([WinAPI]::VK_SPACE, 0, 0, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_SPACE, 0, 2, [UIntPtr]::Zero) }
                    "left"      { [WinAPI]::keybd_event([WinAPI]::VK_LEFT, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_LEFT, 0, 3, [UIntPtr]::Zero) }
                    "up"        { [WinAPI]::keybd_event([WinAPI]::VK_UP, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_UP, 0, 3, [UIntPtr]::Zero) }
                    "right"     { [WinAPI]::keybd_event([WinAPI]::VK_RIGHT, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_RIGHT, 0, 3, [UIntPtr]::Zero) }
                    "down"      { [WinAPI]::keybd_event([WinAPI]::VK_DOWN, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_DOWN, 0, 3, [UIntPtr]::Zero) }
                    "win"       { [WinAPI]::keybd_event([WinAPI]::VK_LWIN, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_LWIN, 0, 3, [UIntPtr]::Zero) }
                }
            }
            "hotkey" {
                $combo = $cmd.combo
                switch ($combo) {
                    "win+d" {
                        [WinAPI]::keybd_event([WinAPI]::VK_LWIN, 0, 1, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event(0x44, 0, 0, [UIntPtr]::Zero) # D
                        [WinAPI]::keybd_event(0x44, 0, 2, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_LWIN, 0, 3, [UIntPtr]::Zero)
                    }
                    "alt+tab" {
                        [WinAPI]::keybd_event([WinAPI]::VK_MENU, 0, 0, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_TAB, 0, 0, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_TAB, 0, 2, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_MENU, 0, 2, [UIntPtr]::Zero)
                    }
                    "ctrl+c" {
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event(0x43, 0, 0, [UIntPtr]::Zero) # C
                        [WinAPI]::keybd_event(0x43, 0, 2, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 2, [UIntPtr]::Zero)
                    }
                    "ctrl+v" {
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event(0x56, 0, 0, [UIntPtr]::Zero) # V
                        [WinAPI]::keybd_event(0x56, 0, 2, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 2, [UIntPtr]::Zero)
                    }
                    "ctrl+z" {
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event(0x5A, 0, 0, [UIntPtr]::Zero) # Z
                        [WinAPI]::keybd_event(0x5A, 0, 2, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 2, [UIntPtr]::Zero)
                    }
                    "ctrl+a" {
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 0, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event(0x41, 0, 0, [UIntPtr]::Zero) # A
                        [WinAPI]::keybd_event(0x41, 0, 2, [UIntPtr]::Zero)
                        [WinAPI]::keybd_event([WinAPI]::VK_CONTROL, 0, 2, [UIntPtr]::Zero)
                    }
                }
            }
            "media" {
                $sub = $cmd.type
                switch ($sub) {
                    "play_pause"  { [WinAPI]::keybd_event([WinAPI]::VK_MEDIA_PLAY, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_MEDIA_PLAY, 0, 3, [UIntPtr]::Zero) }
                    "next"        { [WinAPI]::keybd_event([WinAPI]::VK_MEDIA_NEXT, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_MEDIA_NEXT, 0, 3, [UIntPtr]::Zero) }
                    "prev"        { [WinAPI]::keybd_event([WinAPI]::VK_MEDIA_PREV, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_MEDIA_PREV, 0, 3, [UIntPtr]::Zero) }
                    "volume_up"   { [WinAPI]::keybd_event([WinAPI]::VK_VOLUME_UP, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_VOLUME_UP, 0, 3, [UIntPtr]::Zero) }
                    "volume_down" { [WinAPI]::keybd_event([WinAPI]::VK_VOLUME_DOWN, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_VOLUME_DOWN, 0, 3, [UIntPtr]::Zero) }
                    "mute"        { [WinAPI]::keybd_event([WinAPI]::VK_VOLUME_MUTE, 0, 1, [UIntPtr]::Zero); [WinAPI]::keybd_event([WinAPI]::VK_VOLUME_MUTE, 0, 3, [UIntPtr]::Zero) }
                }
            }
            "system" {
                $sub = $cmd.type
                switch ($sub) {
                    "lock"     { rundll32.exe user32.dll,LockWorkStation }
                    "sleep"    { rundll32.exe powrprof.dll,SetSuspendState 0,1,0 }
                    "shutdown" { shutdown /s /t 0 }
                    "restart"  { shutdown /r /t 0 }
                }
            }
            "launch" {
                $app = $cmd.app
                switch ($app) {
                    "browser"   { Start-Process "https://google.com" }
                    "youtube"   { Start-Process "https://youtube.com" }
                    "notepad"   { Start-Process "notepad.exe" }
                    "calc"      { Start-Process "calc.exe" }
                    "explorer"  { Start-Process "explorer.exe" }
                    "taskmgr"   { Start-Process "taskmgr.exe" }
                    "cmd"       { Start-Process "cmd.exe" }
                }
            }
            "screenshot" {
                try {
                    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
                    $bmp = New-Object System.Drawing.Bitmap($bounds.Width, $bounds.Height)
                    $graphics = [System.Drawing.Graphics]::FromImage($bmp)
                    $graphics.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)

                    # Scale down for fast transmission (e.g. max width 960)
                    $targetWidth = 960
                    $targetHeight = [int]($bounds.Height * ($targetWidth / $bounds.Width))
                    $resized = New-Object System.Drawing.Bitmap($targetWidth, $targetHeight)
                    $gResized = [System.Drawing.Graphics]::FromImage($resized)
                    $gResized.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::Low
                    $gResized.DrawImage($bmp, 0, 0, $targetWidth, $targetHeight)

                    $ms = New-Object System.IO.MemoryStream
                    $resized.Save($ms, [System.Drawing.Imaging.ImageFormat]::Jpeg)
                    $bytes = $ms.ToArray()
                    $base64 = [Convert]::ToBase64String($bytes)

                    $graphics.Dispose()
                    $gResized.Dispose()
                    $bmp.Dispose()
                    $resized.Dispose()
                    $ms.Dispose()

                    $outJson = @{ type = "screenshot"; data = $base64; width = $bounds.Width; height = $bounds.Height } | ConvertTo-Json -Compress
                    [Console]::WriteLine($outJson)
                } catch {
                    Write-Host "SCREENSHOT_ERROR: $_"
                }
            }
        }
    } catch {
        # ignore parse error
    }
}
