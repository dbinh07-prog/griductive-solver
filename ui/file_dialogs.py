"""File selection without requiring Tcl/Tk on Windows."""
import sys

import pygame


def choose_file(title, filetypes, *, save=False, default_ext=""):
    if sys.platform == "win32":
        return _windows_dialog(title, filetypes, save, default_ext)

    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    try:
        if save:
            return filedialog.asksaveasfilename(
                parent=root, title=title, filetypes=filetypes, defaultextension=default_ext
            )
        return filedialog.askopenfilename(parent=root, title=title, filetypes=filetypes)
    finally:
        root.destroy()


def _windows_dialog(title, filetypes, save, default_ext):
    import ctypes
    from ctypes import wintypes

    # OPENFILENAMEW, Windows common dialogs. Keep pointer-sized fields on 64-bit.
    class OpenFileName(ctypes.Structure):
        _fields_ = [
            ("lStructSize", wintypes.DWORD),
            ("hwndOwner", wintypes.HWND),
            ("hInstance", wintypes.HINSTANCE),
            ("lpstrFilter", wintypes.LPCWSTR),
            ("lpstrCustomFilter", wintypes.LPWSTR),
            ("nMaxCustFilter", wintypes.DWORD),
            ("nFilterIndex", wintypes.DWORD),
            ("lpstrFile", wintypes.LPWSTR),
            ("nMaxFile", wintypes.DWORD),
            ("lpstrFileTitle", wintypes.LPWSTR),
            ("nMaxFileTitle", wintypes.DWORD),
            ("lpstrInitialDir", wintypes.LPCWSTR),
            ("lpstrTitle", wintypes.LPCWSTR),
            ("Flags", wintypes.DWORD),
            ("nFileOffset", wintypes.WORD),
            ("nFileExtension", wintypes.WORD),
            ("lpstrDefExt", wintypes.LPCWSTR),
            ("lCustData", wintypes.LPARAM),
            ("lpfnHook", ctypes.c_void_p),
            ("lpTemplateName", wintypes.LPCWSTR),
            ("pvReserved", ctypes.c_void_p),
            ("dwReserved", wintypes.DWORD),
            ("FlagsEx", wintypes.DWORD),
        ]

    filters = []
    for label, pattern in filetypes:
        filters.extend((label, pattern))
    filter_text = "\0".join(filters) + "\0\0"
    filename = ctypes.create_unicode_buffer(32768)
    options = OpenFileName()
    options.lStructSize = ctypes.sizeof(options)
    if pygame.display.get_init() and pygame.display.get_surface() is not None:
        options.hwndOwner = pygame.display.get_wm_info().get("window")
    options.lpstrFilter = filter_text
    options.nFilterIndex = 1
    options.lpstrFile = ctypes.cast(filename, wintypes.LPWSTR)
    options.nMaxFile = len(filename)
    options.lpstrTitle = title
    options.lpstrDefExt = default_ext.lstrip(".") or None
    # Explorer style, existing folder, hide readonly, preserve working directory.
    options.Flags = 0x00080000 | 0x00000800 | 0x00000004 | 0x00000008
    options.Flags |= 0x00000002 if save else 0x00001000

    dialogs = ctypes.WinDLL("comdlg32", use_last_error=True)
    select = dialogs.GetSaveFileNameW if save else dialogs.GetOpenFileNameW
    select.argtypes = [ctypes.POINTER(OpenFileName)]
    select.restype = wintypes.BOOL
    dialogs.CommDlgExtendedError.restype = wintypes.DWORD
    if select(ctypes.byref(options)):
        return filename.value
    error = dialogs.CommDlgExtendedError()
    if error:
        raise OSError(f"Windows file dialog failed (0x{error:04x})")
    return ""  # Cancel is not an error.
