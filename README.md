# WADForge

Texture packer & WAD editor for Quake 1 (WAD2) and GoldSrc/HL (WAD3).

## Features

- **Load, create, and inspect** WAD files — view all textures, resolutions, and byte sizes
- **Pack textures** from a workspace folder into a WAD, with MipTex mipmap compilation
- **Export** individual or batch textures from a WAD to images (BMP, PNG, etc.)
- **Replace** a texture inside a WAD in-place without touching other entries
- **Rename / Delete** textures in the workspace or inside the WAD
- **Convert** between WAD2 and WAD3 formats
- **Texture preview** with zoom, 1:1 toggle, checkerboard alpha grid, and pixel coordinate info
- **Search / filter** workspace images by name
- Supports BMP, PNG, TGA, PCX, JPEG, GIF imports
- Catppuccin Mocha dark theme with color-coded log panel
- High DPI awareness for crisp rendering on Windows
- Persistent workspace path via `config.json`


## Requirements

- **Python 3.9+**
- **Pillow (PIL)** — `pip install Pillow`
- **tkinter** — bundled with standard Python on Windows; on Linux install `python3-tk`

## Quick Start

```bash
pip install Pillow
python main.py
```

## Usage

1. Set a **workspace folder** where your source images live, or restore defaults.
2. **Select** or **Create** a target WAD file.
3. Choose the **WAD Format** (WAD2 for Quake 1, WAD3 for Half-Life).
4. Select images in the workspace panel and click **Pack Selected Textures** to build them into the WAD.
5. Browse textures in the **WAD panel** — export, replace, rename, or delete as needed.
6. Use **Convert Format** to swap between WAD2 / WAD3 architecture.

## Project Structure

```
WADForge/
├── main.py       # Entry point — DPI awareness & Tk root
├── GUI.py        # All tkinter UI code (WADForgeApp class)
├── backend.py    # Core WAD I/O, mipmap compiler, business logic
└── config.json   # Persisted workspace path
```

## Supported Games

| Format | Engine    | Games                                      |
|--------|-----------|--------------------------------------------|
| WAD2   | idTech 2  | Quake, Hexen II                            |
| WAD3   | GoldSrc   | Half-Life, Counter-Strike 1.6, Team Fortress Classic, Day of Defeat, Sven Co-op |

## License

MIT
