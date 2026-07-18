# WADForge

Texture packer & WAD editor for Quake 1 (WAD2) and GoldSrc/HL (WAD3).

## Features

- **Load, create, and inspect** WAD files — view all textures, resolutions, and byte sizes
- **Pack textures** from a workspace folder into a WAD, with MipTex mipmap compilation
- **Export** individual or batch textures from a WAD to images (BMP or PNG, configurable default)
- **Replace** a texture inside a WAD in-place with dimension validation and confirmation prompt
- **Rename / Delete** textures — workspace deletions move files to the Recycle Bin; WAD texture deletions are permanent and require confirmation
- **Keyboard shortcuts** — F5 to refresh all panels, Delete key for quick texture removal (when not focused on a text field)
- **Convert** between WAD2 and WAD3 formats (button in header bar)
- **Texture preview** with zoom (Ctrl+Wheel), 1:1 toggle, clickable Fit, checkerboard alpha grid, and pixel coordinate info
- **Search / filter** workspace images **and WAD textures** by name in real-time
- **Context-aware action buttons** — only applicable buttons are shown based on selection type
- **Hover tooltips** on all action buttons explaining their function
- **Settings panel** for persistent export format preference (BMP/PNG) and workspace defaults
- **Collapsible console log** with color-coded entries and toggle button
- **Status validation** — warns on name truncation, dimension issues, and duplicate conflicts
- Supports BMP, PNG, TGA, PCX, JPEG, GIF imports
- Catppuccin Mocha dark theme
- High DPI awareness for crisp rendering on Windows
- Persistent settings via `config.json` (auto-saved on workspace browse)

## Requirements

- **Python 3.9+**
- **Pillow (PIL)** — `pip install Pillow`
- **send2trash** — `pip install send2trash` (safe workspace deletion)
- **tkinter** — bundled with standard Python on Windows; on Linux install `python3-tk`

## Quick Start

```bash
pip install Pillow send2trash
python main.py
```

On first launch, `config.json` is created automatically. See `templateconfig.json` for the expected format.

## Image of the Script

<img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/ba877e7c-03d8-44b8-bafb-06ed99a8e63c" />


## Usage

1. Set a **workspace folder** where your source images live (Browse auto-saves your choice).
2. **Select** or **Create** a target WAD file.
3. Choose the **WAD Format** (WAD2 for Quake 1, WAD3 for Half-Life).
4. Select images in the workspace panel and click **Pack Selected Textures** to build them into the WAD.
5. Browse textures in the **WAD panel** — use the filter bar to search, export, replace, rename, or delete as needed.
6. Use **↔ Convert** in the header bar to swap between WAD2 / WAD3 architecture.
7. Click **⚙ Settings** to change default export format or restore workspace defaults.
8. Click **☰ Console** to toggle the log panel.

For full documentation see [Documentation.md](Documentation.md).

## Project Structure

```
WADForge/
├── main.py              # Entry point — DPI awareness & Tk root
├── GUI.py               # All tkinter UI code (WADForgeApp class)
├── backend.py           # Core WAD I/O, mipmap compiler, business logic
├── build_linux.sh       # Linux PyInstaller build script
├── templateconfig.json  # Reference for config.json structure
├── .gitignore
└── Documentation.md
```

## Supported Games

| Format | Engine    | Games                                      |
|--------|-----------|--------------------------------------------|
| WAD2   | idTech 2  | Quake, Hexen II                            |
| WAD3   | GoldSrc   | Half-Life, Counter-Strike 1.6, Team Fortress Classic, Day of Defeat, Sven Co-op |

## License

MIT
