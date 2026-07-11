"""
main.py — Application entry point.

Creates the Tk root window, enables High DPI awareness,
maximizes the window while keeping the taskbar visible, and launches the GUI.
"""

import tkinter as tk
import os
import sys
from GUI import WADForgeApp

def enable_high_dpi_awareness():
    """
    Enables Windows High DPI awareness so text and UI elements 
    render sharply instead of blurry on high-resolution displays.
    """
    if os.name == 'nt':  # Only applies to Windows platforms
        try:
            import ctypes
            # Try to use Per-Monitor DPI Awareness V2 or V1 (Windows 8.1 / 10 / 11)
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2) # 2 = PROCESS_PER_MONITOR_DPI_AWARE
            except Exception:
                try:
                    ctypes.windll.shcore.SetProcessDpiAwareness(1) # 1 = PROCESS_SYSTEM_DPI_AWARE
                except Exception:
                    # Fallback for older Windows versions (Windows Vista / 7)
                    ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass # Fail gracefully if ctypes isn't supported or fails

def main():
    # 1. Enable proper crisp High DPI resolution scaling
    enable_high_dpi_awareness()
    
    root = tk.Tk()
    
    # 2. Open the window in a maximized state (takes the whole screen, taskbar stays visible!)
    #    We try 'zoomed' first (standard for modern Tcl/Tk), then fallback to standard platform methods.
    try:
        root.state('zoomed')
    except tk.TclError:
        try:
            if os.name == 'nt':
                root.state('maximized')
            else:
                root.attributes('-zoomed', True)
        except Exception:
            pass # Fallback completely if standard window dimensions are required

    # Initialize the app layout
    app = WADForgeApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()