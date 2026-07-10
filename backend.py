"""
backend.py — Core WAD data structures, BMP compilation, and business-logic operations.

All functions here are pure logic — no tkinter imports, no GUI calls.
Functions return values or raise exceptions; the GUI layer handles display.
"""

import struct
import os
import json
import hashlib
import re
from PIL import Image

CONFIG_FILE = "config.json"

# ----------------------------------------------------------------------
# Settings and Configuration Sub-Engine
# ----------------------------------------------------------------------

def get_executable_dir():
    """Returns the absolute directory path where this script/executable resides."""
    return os.getcwd()

def load_settings():
    """
    Loads config.json profile records.
    If corrupted or not found, falls back safely to executable directory by default.
    """
    default_dir = get_executable_dir()
    default_settings = {"workspace_dir": default_dir}
    
    if not os.path.exists(CONFIG_FILE):
        return default_settings
        
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if "workspace_dir" not in data or not data["workspace_dir"]:
                data["workspace_dir"] = default_dir
            return data
    except Exception:
        return default_settings

def save_settings(workspace_dir):
    """Saves the target workspace folder path selection explicitly into config.json."""
    try:
        data = {"workspace_dir": workspace_dir}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return True
    except Exception:
        return False

def restore_default_settings():
    """Drops the active configurations and reverts settings safely back to defaults."""
    default_dir = get_executable_dir()
    save_settings(default_dir)
    return default_dir

# ----------------------------------------------------------------------
# Core WAD Data Structures
# ----------------------------------------------------------------------

class WadEntry:
    def __init__(self, name, data, type_byte=0x44, cmprs=0):
        # Textures are strictly clamped to a maximum of 15 characters plus null terminator
        self.name = name.lower()[:15]
        self.data = data
        self.type_byte = type_byte
        self.cmprs = cmprs

class WadFile:
    def __init__(self, magic=b'WAD2'):
        self.magic = magic
        self.entries = {}

    def add_entry(self, entry):
        self.entries[entry.name] = entry

    def delete_entry(self, name):
        name = name.lower()[:15]
        if name in self.entries:
            del self.entries[name]
            return True
        return False

    def rename_entry(self, old_name, new_name):
        old_name = old_name.lower()[:15]
        new_name = new_name.lower()[:15]
        if old_name in self.entries and old_name != new_name:
            entry = self.entries.pop(old_name)
            entry.name = new_name
            
            # Synchronize internal Miptex header texture name string safely (first 16 bytes)
            if len(entry.data) >= 16:
                name_bytes = new_name.encode('ascii', errors='ignore')[:15].ljust(16, b'\x00')
                entry.data = name_bytes + entry.data[16:]
            self.entries[new_name] = entry
            return True
        return False

    @classmethod
    def load(cls, filepath):
        """Unpacks and loads a binary .WAD structure completely into instance space."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Target WAD structure archive not found at path: {filepath}")
            
        if os.path.getsize(filepath) < 12:
            return cls(b'WAD2')

        with open(filepath, 'rb') as f:
            header = f.read(12)
            if len(header) < 12:
                return cls(b'WAD2')
                
            try:
                magic, num_lumps, infotable_offset = struct.unpack('<4sII', header)
            except struct.error:
                return cls(b'WAD2')
                
            if magic not in (b'WAD2', b'WAD3'):
                raise ValueError(f"Unsupported WAD type identifier: {magic.decode('ascii', errors='ignore')}")
                
            wad = cls(magic)
            
            f.seek(infotable_offset)
            directory_data = f.read(num_lumps * 32)
            
            lump_info_list = []
            for i in range(num_lumps):
                offset = i * 32
                lump_bytes = directory_data[offset : offset + 32]
                
                if len(lump_bytes) < 32:
                    break
                    
                try:
                    # FIXED: Changed format string to expect and unpack exactly 32 bytes cleanly
                    filepos, disksize, size, type_byte, cmprs, pad, name_raw = struct.unpack('<IIIbB2s16s', lump_bytes)
                    name = name_raw.split(b'\x00')[0].decode('ascii', errors='ignore').lower()
                    lump_info_list.append((name, filepos, disksize, type_byte, cmprs))
                except struct.error:
                    break
                
            # Extract independent data streams into unique object references
            for name, filepos, disksize, type_byte, cmprs in lump_info_list:
                f.seek(filepos)
                data = f.read(disksize)
                wad.add_entry(WadEntry(name, data, type_byte, cmprs))
                
            return wad

    def save(self, filepath):
        """Serializes and records current image collections back into standard binary .WAD arrays."""
        with open(filepath, 'wb') as f:
            # Write structured placeholder info table parameters sequentially
            f.write(struct.pack('<4sII', self.magic, len(self.entries), 0))
            
            directory_records = []
            for name, entry in self.entries.items():
                current_pos = f.tell()
                f.write(entry.data)
                disk_size = len(entry.data)
                
                # Structure the core directory map tuple object
                directory_records.append((current_pos, disk_size, disk_size, entry.type_byte, entry.cmprs, name))
                
            infotable_offset = f.tell()
            
            # Serialize the continuous directory indexing block entries (32 bytes per lump)
            for filepos, disksize, size, type_byte, cmprs, name in directory_records:
                name_bytes = name.encode('ascii', errors='ignore')[:15].ljust(16, b'\x00')
                # FIXED: Writes out using the identical 32-byte pattern alignment layout
                f.write(struct.pack('<IIIbB2s16s', filepos, disksize, size, type_byte, cmprs, b'\x00\x00', name_bytes))
                
            # Seek back to correct the true directory table offset entry
            f.seek(4)
            f.write(struct.pack('<II', len(self.entries), infotable_offset))

# ----------------------------------------------------------------------
# Business-Logic and Image Manipulation Subsystem
# ----------------------------------------------------------------------

def analyze_liquid_texture_name(name):
    """
    Validates classic engine texture string schemas.
    Identifies custom animated sequence prefixes (*water, *slime, *lava).
    """
    cleaned_name = name.lower().strip()
    if not cleaned_name.startswith("*"):
        return None
        
    if cleaned_name.startswith("*slime"):
        return "Slime Liquid (Hazardous)"
    elif cleaned_name.startswith("*lava"):
        return "Lava Liquid (Lethal)"
    else:
        return "Water Liquid (Swimmable)"

def scan_workspace_bmps(folder):
    """
    Scans workspace for BMP images and evaluates eligibility parameters.
    Checks resolution boundaries and validates name patterns.
    """
    if not os.path.exists(folder):
        raise FileNotFoundError(f"Target folder configuration mapping invalid: '{folder}'")
        
    detected = []
    warnings = []
    seen_texnames = {}
    
    files = [f for f in os.listdir(folder) if f.lower().endswith('.bmp')]
    
    for fname in files:
        fpath = os.path.join(folder, fname)
        base_name, _ = os.path.splitext(fname)
        
        # Safe translation filter mapping for classic texture indexing standard parameters
        texname = re.sub(r'[^a-zA-Z0-9_\-*{}#=+\[\]]', '', base_name).lower()[:15]
        
        if not texname:
            detected.append({"filename": fname, "texname": "unnamed", "path": fpath, "res": "0x0", "format": "Unknown", "valid": False, "status": "ERR: Empty alpha key name."})
            continue
            
        try:
            with Image.open(fpath) as img:
                w, h = img.size
                img_format = "Indexed (8-bit)" if img.mode == 'P' else img.mode
                
            res_str = f"{w}x{h}"
            status = "Ready"
            valid = True
            
            # Quake/GoldSrc requirement: Dimensions must be divisible by 16
            if w % 16 != 0 or h % 16 != 0:
                status = "ERR: Dimensions not divisible by 16."
                valid = False
            elif w > 512 or h > 512:
                status = "WARN: Oversized texture boundary asset map."
                warnings.append(("warning", f"Asset image '{fname}' dimensions exceed optimal real-time bounds ({res_str})."))
                
            # Scan and track classic liquid sequence groups
            liquid_type = analyze_liquid_texture_name(texname)
            if liquid_type and valid:
                status = "Ready (Liquid Anim)"
                
            # Duplicate detection inside workspace tracking
            if texname in seen_texnames:
                status = f"CONFLICT: Maps to same slot as '{seen_texnames[texname]}'"
                valid = False
            else:
                seen_texnames[texname] = fname
                
            detected.append({"filename": fname, "texname": texname, "path": fpath, "res": res_str, "format": img_format, "valid": valid, "status": status})
            
        except Exception as e:
            detected.append({"filename": fname, "texname": texname, "path": fpath, "res": "0x0", "format": "Corrupted", "valid": False, "status": f"ERR: {str(e)}"})
            
    return detected, warnings

# ----------------------------------------------------------------------
# Standard Quake 1 Palette (256 colours × 3 bytes RGB)
# Used to display WAD2 textures which store only palette indices, not colours.
# ----------------------------------------------------------------------

QUAKE_PALETTE_HEX = (
    "0000000f0f0f1f1f1f2f2f2f3f3f3f4b4b4b5b5b5b6b6b6b7b7b7b8b8b8b9b9b9b"
    "abababbbbbbbcbcbcbdbdbdbebebeb0f0b07170f0b1f170b271b0f2f2313372b17"
    "3f2f174b371b533b1b5b431f634b1f6b531f73571f7b5f238367238f6f230b0b0f"
    "13131b1b1b272727332f2f3f37374b3f3f574747674f4f735b5b7f63638b6b6b97"
    "7373a37b7baf8383bb8b8bcb0000000707000b0b001313001b1b002323002b2b07"
    "2f2f073737073f3f074747074b4b0b53530b5b5b0b63630b6b6b0f0700000f0000"
    "1700001f00002700002f00003700003f00004700004f00005700005f0000670000"
    "6f00007700007f00001313001b1b002323002f2b00372f004337004b3b07574307"
    "5f47076b4b0b77530f8357138b5b13975f1ba3631faf67232313072f170b3b1f0f"
    "4b2313572b17632f1f7337237f3b2b8f43339f4f33af632fbf772fcf8f2bdfab27"
    "efcb1ffff31b0b07001b13002b230f372b1347331b533723633f2b6f47337f533f"
    "8b5f479b6b53a77b5fb7876bc3937bd3a38be3b397ab8ba39f7f979373878b677b"
    "7f5b6f7753636b4b575f3f4b5737434b2f3743272f371f232b171b231313170b0b"
    "0f0707bb739faf6b8fa35f839757778b4f6b7f4b5f7343536b3b4b5f333f532b37"
    "47232b3b1f232f171b231313170b0b0f0707dbc3bbcbb3a7bfa39baf978ba3877b"
    "977b6f876f5f7b63536b57475f4b3b533f33433327372b1f271f171b130f0f0b07"
    "6f837b677b6f5f7367576b5f4f6357475b4f3f5347374b3f2f43372b3b2f233327"
    "1f2b1f1723170f1b130b130b070b07fff31befdf17dbcb13cbb70fbba70fab970b"
    "9b83078b73077b63076b53005b47004b37003b2b002b1f001b0f000b07000000ff"
    "0b0bef1313df1b1bcf2323bf2b2baf2f2f9f2f2f8f2f2f7f2f2f6f2f2f5f2b2b4f"
    "23233f1b1b2f13131f0b0b0f2b00003b00004b07005f07006f0f007f1707931f07"
    "a3270bb7330fc34b1bcf632bdb7f3be3974fe7ab5fefbf77f7d38ba77b3bb79b37"
    "c7c337e7e3577fbfffabe7ffd7ffff6700008b0000b30000d70000ff0000fff393"
    "fff7c7ffffff9f5b53"
)
QUAKE_PALETTE = bytes.fromhex(QUAKE_PALETTE_HEX)

def decode_miptex_to_image(lump_data, wad_format):
    """
    Parses a binary Miptex texture lump from a WAD and reconstructs a standard PIL Image object.
    Supports both WAD2 (Quake, external palette) and WAD3 (Half-Life, embedded palette).
    """
    if len(lump_data) < 40:
        raise ValueError("Lump data truncated; unable to process standard texture header layout.")
        
    name_bytes, width, height, mip1_off, mip2_off, mip3_off, mip4_off = struct.unpack('<16sIIIIII', lump_data[:40])
    
    mip1_size = width * height
    mip1_pixels = lump_data[mip1_off : mip1_off + mip1_size]
    
    img = Image.new("P", (width, height))
    img.putdata(list(mip1_pixels))
    
    if wad_format == "WAD3":
        # WAD3 features an embedded palette structure layout located immediately after mip data
        palette_header_offset = mip4_off + (width // 8) * (height // 8)
        if len(lump_data) >= palette_header_offset + 2 + 768:
            num_colors = struct.unpack('<H', lump_data[palette_header_offset : palette_header_offset + 2])[0]
            if num_colors == 256:
                palette_bytes = lump_data[palette_header_offset + 2 : palette_header_offset + 2 + 768]
                img.putpalette(palette_bytes)
                return img
                
    # Fallback for WAD2: apply the standard Quake hardware palette
    img.putpalette(QUAKE_PALETTE)
    return img

def read_wad_contents(wad_path):
    """Reads texture records from a target WAD file container archive map structure."""
    wad = WadFile.load(wad_path)
    entries_list = []
    wad_format_str = wad.magic.decode('ascii', errors='ignore')
    
    for name, entry in wad.entries.items():
        res_str = "Unknown"
        if len(entry.data) >= 40:
            _, w, h = struct.unpack('<16sII', entry.data[:24])
            res_str = f"{w}x{h}"
            
        entries_list.append({"name": name, "res": res_str, "size": str(len(entry.data))})
        
    return wad_format_str, entries_list

def rename_workspace_file(folder, old_name, new_name):
    """Renames an image file inside the target workspace directory safely."""
    if not new_name.lower().endswith('.bmp'):
        new_name += '.bmp'
    old_path = os.path.join(folder, old_name)
    new_path = os.path.join(folder, new_name)
    if not os.path.exists(old_path):
        raise FileNotFoundError("Source filesystem element target reference unavailable.")
    if os.path.exists(new_path):
        raise FileExistsError(f"An asset with target moniker identity '{new_name}' is already active.")
    os.rename(old_path, new_path)
    return new_name

def rename_wad_entry(wad_path, old_name, new_name):
    """Renames an existing texture lump inside an active WAD archive container."""
    new_cleaned = re.sub(r'[^a-zA-Z0-9_\-*{}#=+\[\]]', '', new_name).lower()[:15]
    if not new_cleaned:
        raise ValueError("The provided texture name string resolved down to an empty key format.")
        
    wad = WadFile.load(wad_path)
    if new_cleaned in wad.entries:
        raise ValueError(f"A texture labeled '{new_cleaned}' already occupies a slot inside this WAD container.")
        
    if wad.rename_entry(old_name, new_cleaned):
        wad.save(wad_path)
        return new_cleaned
    raise KeyError("The requested transaction reference index could not be located inside this WAD.")

def delete_workspace_files(folder, filenames):
    """Deletes one or more files from the active workspace directory path."""
    success_count = 0
    errors = []
    for fname in filenames:
        fpath = os.path.join(folder, fname)
        try:
            if os.path.exists(fpath):
                os.remove(fpath)
                success_count += 1
        except Exception as e:
            errors.append((fname, str(e)))
    return success_count, errors

def delete_wad_entries(wad_path, names):
    """Removes selected texture entry lumps completely from a WAD archive container."""
    wad = WadFile.load(wad_path)
    count = 0
    for name in names:
        if wad.delete_entry(name):
            count += 1
    if count > 0:
        wad.save(wad_path)
    return count

def export_wad_entry(wad_path, entry_name, output_path, wad_format):
    """
    Decodes a binary Miptex entry from a WAD and outputs it to disk.
    PIL dynamically resolves the targeted image format (.png, .bmp, .jpg) via extension.
    """
    wad = WadFile.load(wad_path)
    if entry_name not in wad.entries:
        raise KeyError(f"Texture asset '{entry_name}' not found within active WAD directory matrix.")
        
    entry = wad.entries[entry_name]
    img = decode_miptex_to_image(entry.data, wad_format)
    img.save(output_path)

def export_wad_entries_bulk(wad_path, names, output_dir, wad_format):
    """Exports multiple texture lumps from a WAD container to a targeted directory path."""
    wad = WadFile.load(wad_path)
    count = 0
    for name in names:
        if name in wad.entries:
            out_file = os.path.join(output_dir, f"{name}.bmp")
            img = decode_miptex_to_image(wad.entries[name].data, wad_format)
            img.save(out_file)
            count += 1
    return count

def replace_wad_entry(wad_path, entry_name, import_image_path, wad_format):
    """Replaces a texture inside a WAD with an updated asset file image sequence link."""
    wad = WadFile.load(wad_path)
    if entry_name not in wad.entries:
        raise KeyError("Target WAD container address pointer index reference invalid.")
        
    with Image.open(import_image_path) as img:
        w, h = img.size
        
    # Retain the exact dimensions from the internal header entry block structure
    _, old_w, old_h = struct.unpack('<16sII', wad.entries[entry_name].data[:24])
    if w != old_w or h != old_h:
        raise ValueError(f"Dimension mismatch error. Replacement file bounds must measure exactly: {old_w}x{old_h}")
        
    lump_data = compile_bmp_to_miptex(import_image_path, entry_name, wad_format)
    wad.entries[entry_name].data = lump_data
    wad.save(wad_path)

def convert_wad_format_file(wad_path, current_format, target_format):
    """Converts WAD container formats between standard WAD2 and WAD3 architectures."""
    wad = WadFile.load(wad_path)
    wad.magic = target_format.encode('ascii')
    type_byte = 0x43 if target_format == "WAD3" else 0x44
    success = 0
    
    for name, entry in wad.entries.items():
        entry.type_byte = type_byte
        if len(entry.data) >= 40:
            _, w, h, m1, m2, m3, m4 = struct.unpack('<16sIIIIII', entry.data[:40])
            expected_wad2_size = m4 + (w // 8) * (h // 8)
            
            if target_format == "WAD3" and len(entry.data) == expected_wad2_size:
                # Append a default 256 color standard template palette entry string 
                fallback_palette = [i for i in range(256) for _ in range(3)]
                entry.data += struct.pack('<H', 256) + bytes(fallback_palette)
                success += 1
            elif target_format == "WAD2" and len(entry.data) > expected_wad2_size:
                entry.data = entry.data[:expected_wad2_size]
                success += 1
                
    wad.save(wad_path)
    return success

def compile_bmp_to_miptex(bmp_path, name, wad_format):
    """
    Compiles an external file asset into a full 4-level mipmapped binary Miptex structure.
    Packs color indices and embeds palette profiles to standard game specifications.
    """
    with Image.open(bmp_path) as img:
        w, h = img.size
        
        # Ensure optimal 8-bit color index quantization mappings safely
        if img.mode == 'P':
            img_p = img
        else:
            img_p = img.convert("P", palette=Image.Palette.ADAPTIVE, colors=256)
            
        raw_indices = list(img_p.getdata())
        palette_bytes = img_p.getpalette()
        
    if not palette_bytes:
        palette_bytes = [i for i in range(256) for _ in range(3)]
    else:
        palette_bytes = palette_bytes[:768]
        if len(palette_bytes) < 768:
            palette_bytes += [0] * (768 - len(palette_bytes))
            
    # Calculate operational byte offset mappings for the 4 Mip structural tiers
    o1 = 40
    o2 = o1 + w * h
    o3 = o2 + (w // 2) * (h // 2)
    o4 = o3 + (w // 4) * (h // 4)
    
    name_bytes = name.encode('ascii', errors='ignore')[:15].ljust(16, b'\x00')
    header = struct.pack('<16sIIIIII', name_bytes, w, h, o1, o2, o3, o4)
    
    # Nearest-neighbor pixel subsampling strategy for low-level mipmap layer arrays
    mip1 = bytes(raw_indices)
    mip2 = bytes([raw_indices[(y * 2) * w + (x * 2)] for y in range(h // 2) for x in range(w // 2)])
    mip3 = bytes([raw_indices[(y * 4) * w + (x * 4)] for y in range(h // 4) for x in range(w // 4)])
    mip4 = bytes([raw_indices[(y * 8) * w + (x * 8)] for y in range(h // 8) for x in range(w // 8)])
    
    lump_data = header + mip1 + mip2 + mip3 + mip4
    
    # Embed standard game engine structure palettes explicitly into WAD3 definitions
    if wad_format == "WAD3":
        num_colors = struct.pack('<H', 256)
        lump_data += num_colors + bytes(palette_bytes)
        
    return lump_data

def pack_textures_to_wad(wad_path, to_pack, wad_format, progress_cb=None):
    """Compiles and merges workspace collections safely directly into binary containers."""
    try:
        wad = WadFile.load(wad_path)
        wad.magic = wad_format.encode('ascii')
    except Exception:
        wad = WadFile(wad_format.encode('ascii'))
        
    type_byte = 0x43 if wad_format == "WAD3" else 0x44
    success_count = 0
    total = len(to_pack)
    
    for i, info in enumerate(to_pack):
        if progress_cb:
            progress_cb(i, total, f"Compiling '{info['filename']}' -> texture name '{info['texname']}'...", "info")
        try:
            # Check for standard liquid naming profiles during runtime integration
            liquid_type = analyze_liquid_texture_name(info["texname"])
            if liquid_type and progress_cb:
                progress_cb(i, total, f"✨ Animated liquid prefix sequence scanned: Mapped to '{info['texname']}' as {liquid_type}.", "info")
                
            lump_data = compile_bmp_to_miptex(info["path"], info["texname"], wad_format)
            entry = WadEntry(info["texname"], lump_data, type_byte=type_byte)
            wad.add_entry(entry)
            success_count += 1
            if progress_cb:
                progress_cb(i + 1, total, f"Successfully compiled '{info['texname']}' ({info['res']})", "success")
        except Exception as e:
            if progress_cb:
                progress_cb(i + 1, total, f"Failed to compile texture lump '{info['filename']}': {str(e)}", "error")
                
    if success_count > 0:
        wad.save(wad_path)
        
    return success_count