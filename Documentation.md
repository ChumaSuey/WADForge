# WADForge — Documentation

## Overview

WADForge is a GUI tool for managing texture archives for GoldSrc (Half-Life) and idTech 2 (Quake) engines. It lets you pack images into WAD files, extract textures from existing WADs, and perform operations like renaming, deleting, replacing, and format conversion.

---

## Installation

### Requirements

- Python 3.9 or newer
- Pillow (`pip install Pillow`)
- tkinter (included with Python on Windows; `python3-tk` on Linux)

### Running

```bash
pip install Pillow
python main.py
```

---

## Interface Layout

```
┌─────────────────────────────────────────────────────────────┐
│  WADForge — Quake/HL Texture Manager   [☰ Console] [⚙ Set] │
├─────────────────────────────────────────────────────────────┤
│  Workspace Folder: [_________] [Browse] [Save] [Restore]   │
│  Target WAD File:  [_________] [Select] [New] [Clear]      │
│  WAD Format: [WAD2 ▼]  (WAD2=Quake, WAD3=Half-Life)  [↻]  │
├──────────────────┬──────────────────┬───────────────────────┤
│ Workspace Images  │ Target WAD Textures│   Texture Preview   │
│ ┌──────────────┐ │ ┌───────────────┐ │  ┌─────────────────┐ │
│ │ filename.bmp │ │ │ TEX_NAME      │ │  │                 │ │
│ │ another.png  │ │ │ WALL01        │ │  │   Preview +     │ │
│ │ ...          │ │ │ ...           │ │  │   zoom controls │ │
│ └──────────────┘ │ └───────────────┘ │  └─────────────────┘ │
│ [Select All] [Clear] │                 │  [Rename] [Delete]  │
│                      │                 │  [Export] [Replace] │
├──────────────────────┴─────────────────┴─────────────────────┤
│ Pack Selected Textures ◄─────────────────────────────────────│
├─────────────────────────────────────────────────────────────┤
│  ☰ Console — Execution Log / Warnings              [Clear]  │
└─────────────────────────────────────────────────────────────┘
```

The action buttons in the preview panel are **context-aware** — only buttons that apply to your current selection are shown.

---

## Panels

### Workspace Images (left panel)

Shows all supported image files in your workspace folder. Columns: filename, texture name, resolution, format, and validation status.

- **Filter**: Type in the filter box to search by filename or texture name.
- **Select All / Clear Selection**: Quick-select or deselect all workspace entries.
- **Validation**: Green = valid, yellow = duplicate name conflict, red = format/size issues.

### Target WAD Textures (middle panel)

Shows all texture entries inside the currently loaded WAD file. Columns: texture name, resolution, and byte size.

- Click a column header to sort by that column.
- Use **Convert Format** to toggle between WAD2 and WAD3 for the loaded file.

### Texture Preview (right panel)

Displays the selected texture with:
- **Checkerboard background** to visualize transparency.
- **Zoom controls**: `−` / `+` / `1:1` buttons, plus mouse wheel.
- **Pixel info**: X, Y coordinates and RGBA values under the cursor.

---

## Action Buttons

The four buttons below the preview are **context-aware**. They appear or hide based on what you have selected.

### Single Workspace File Selected

| Button     | Action |
|------------|--------|
| Rename File | Renames the file on disk (preserves extension) |
| Delete from Disk | Deletes the file from the workspace folder (with confirmation) |

### Multiple Workspace Files Selected

| Button     | Action |
|------------|--------|
| Delete from Disk | Deletes all selected files from the workspace (with confirmation) |

### Single WAD Texture Selected

| Button         | Action |
|----------------|--------|
| Rename Texture | Renames the texture entry inside the WAD (max 15 characters) |
| Delete from WAD | Removes the texture lump from the WAD (with confirmation) |
| Export Texture | Saves the decoded texture as BMP or PNG to a chosen location |
| Replace Texture | Opens a file dialog; replaces the texture's pixel data with an external image (must have the exact same dimensions — the dialog title shows the required size) |

### Multiple WAD Textures Selected

| Button         | Action |
|----------------|--------|
| Delete from WAD | Removes multiple texture lumps from the WAD (with confirmation) |
| Export Textures | Bulk-exports all selected textures to a chosen folder in your default format |

### No Selection

All buttons are hidden. A label shows "Select an image to get started".

---

## Packing Textures

1. Set your **workspace folder** to a directory containing your source images.
2. Open or create a **target WAD file**.
3. Choose the desired **WAD Format** (WAD2 or WAD3).
4. Select images in the workspace panel (multi-select with Ctrl/Cmd+click or Shift+click).
5. Click **Pack Selected Textures**.
6. The progress bar shows compilation status. Each image is compiled into a 4-level mipmapped MipTex lump with proper palette handling.

---

## Exporting Textures

### Single Export

Select one WAD texture and click **Export Texture**. A file dialog lets you choose the location and format (BMP or PNG).

### Bulk Export

Select multiple WAD textures and click **Export Textures**. Choose a destination folder — all textures are saved there in your default format (set in Settings).

---

## Replacing Textures

1. Select a WAD texture and click **Replace Texture**.
2. The file dialog title shows the required dimensions (e.g., "must be 256x256").
3. Choose a replacement image file.
4. A confirmation prompt appears — confirm to proceed.
5. If the image dimensions match the texture, the pixel data is swapped in-place.

**Important**: The replacement image must have the **exact same width and height** as the texture being replaced. The file dialog title tells you the expected size before you pick a file.

---

## Renaming / Deleting

- **Workspace side**: Rename and Delete operate on physical files on disk.
- **WAD side**: Rename and Delete operate on texture entries inside the loaded WAD archive.
- All destructive operations show a confirmation dialog.
- Button labels update dynamically to reflect what they act on ("Delete from Disk" vs "Delete from WAD").

---

## Settings

Click **⚙ Settings** in the top-right header to open the settings dialog.

### Default Export Format

Choose **BMP** or **PNG** as the default format for:
- **Bulk exports** — always uses this format
- **Single exports** — the file dialog defaults to this format (you can still change it per-export)

The setting is saved to `config.json` and persists between sessions.

---

## Console Log

The console log is hidden by default for a cleaner interface. Click **☰ Console** in the top-right header to show/hide it.

- Log entries are color-coded: white (info), yellow (warning), red (error), green (success).
- Click **Clear Log** to reset the console.
- The log accumulates messages even when hidden.

---

## WAD Format Conversion

The **Convert Format** button toggles between WAD2 and WAD3 for the loaded WAD:

- **WAD2 → WAD3**: Appends a 256-color palette to each texture lump (placeholder gray ramp). Pixel data is untouched.
- **WAD3 → WAD2**: Strips the palette from each texture lump. Pixel data is untouched.
- **WAD2 → WAD3 → WAD2** is lossless — the file is byte-for-byte restored.
- A confirmation dialog asks before saving, as the WAD file is overwritten.

---

## Supported Image Formats

### Import (Pack)
- BMP, PNG, TGA, PCX, JPEG, GIF

### Export
- BMP, PNG

---

## WAD2 vs WAD3

| | WAD2 | WAD3 |
|---|---|---|
| **Engine** | Quake (idTech 2) | Half-Life (GoldSrc) |
| **Palette** | Global Quake hardware palette | Per-texture embedded palette |
| **Type byte** | `0x44` | `0x43` |
| **Magic** | `WAD2` | `WAD3` |

When packing textures in WAD2 mode, colors are automatically remapped to the Quake hardware palette. WAD3 mode preserves custom palettes (embedded directly in each lump).

---

## Configuration File

`config.json` stores your preferences:

```json
{
    "workspace_dir": "C:/path/to/your/images",
    "export_format": "bmp"
}
```

- **workspace_dir**: Default workspace folder path.
- **export_format**: `"bmp"` or `"png"` — default export format.

Click **Save As Default** next to the workspace path to persist your folder. Settings are auto-saved when changed in the Settings dialog.

---

## Tips

- **Hover over any action button** to see a tooltip explaining what it does.
- **Double-click** a workspace image to preview it.
- Use **right-click** on tree items for quick access (context menus coming soon).
- The **status column** in the workspace panel warns you about naming conflicts, unsupported formats, or resolution issues before packing.
