# WADForge

Texture packer & WAD editor for Quake 1 (WAD2) and GoldSrc/HL (WAD3).

## Features

- **Load, create, and inspect** WAD files — view all textures, resolutions, and byte sizes
- **Pack textures** from a workspace folder into a WAD, with MipTex mipmap compilation
- **Export** individual or batch textures from a WAD to images (BMP or PNG, configurable default)
- **Replace** a texture inside a WAD in-place with dimension validation and confirmation prompt
- **Rename / Delete** textures on disk (workspace) or inside the WAD, with context-aware button labels
- **Convert** between WAD2 and WAD3 formats
- **Texture preview** with zoom, 1:1 toggle, checkerboard alpha grid, and pixel coordinate info
- **Search / filter** workspace images by name
- **Context-aware action buttons** — only applicable buttons are shown based on selection type
- **Hover tooltips** on all action buttons explaining their function
- **Settings panel** for persistent export format preference (BMP/PNG)
- **Collapsible console log** with color-coded entries and toggle button
- Supports BMP, PNG, TGA, PCX, JPEG, GIF imports
- Catppuccin Mocha dark theme
- High DPI awareness for crisp rendering on Windows
- Persistent settings via `config.json`

## Requirements

- **Python 3.9+**
- **Pillow (PIL)** — `pip install Pillow`
- **tkinter** — bundled with standard Python on Windows; on Linux install `python3-tk`

## Quick Start

```bash
pip install Pillow
python main.py
```

## Image of the Script

<img width="1920" height="1020" alt="image" src="https://github.com/user-attachments/assets/a1830595-58f2-4342-beb0-fc9dc854ecbb" />

## Usage

1. Set a **workspace folder** where your source images live, or restore defaults.
2. **Select** or **Create** a target WAD file.
3. Choose the **WAD Format** (WAD2 for Quake 1, WAD3 for Half-Life).
4. Select images in the workspace panel and click **Pack Selected Textures** to build them into the WAD.
5. Browse textures in the **WAD panel** — export, replace, rename, or delete as needed.
6. Use **Convert Format** to swap between WAD2 / WAD3 architecture.
7. Click **⚙ Settings** to change the default export format (BMP/PNG).
8. Click **☰ Console** to toggle the log panel.

For full documentation see [Documentation.md](Documentation.md).

## Project Structure

```
WADForge/
├── main.py       # Entry point — DPI awareness & Tk root
├── GUI.py        # All tkinter UI code (WADForgeApp class)
├── backend.py    # Core WAD I/O, mipmap compiler, business logic
├── config.json   # Persisted settings (workspace path, export format)
└── Documentation.md
```

## Supported Games

| Format | Engine    | Games                                      |
|--------|-----------|--------------------------------------------|
| WAD2   | idTech 2  | Quake, Hexen II                            |
| WAD3   | GoldSrc   | Half-Life, Counter-Strike 1.6, Team Fortress Classic, Day of Defeat, Sven Co-op |

## License

MIT
