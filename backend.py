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
            # Ensure the structure keys are present, fallback if missing
            if "workspace_dir" not in data or not data["workspace_dir"]:
                data["workspace_dir"] = default_dir
            return data
    except Exception:
        return default_settings

def save_settings(workspace_dir):
    """Saves the target workspace folder path selection explicitly into the config JSON."""
    try:
        settings = {"workspace_dir": workspace_dir}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        return True
    except Exception:
        return False

def restore_default_settings():
    """Removes explicit definitions and resets configuration back to executable folder defaults."""
    default_dir = get_executable_dir()
    save_settings(default_dir)
    return default_dir

# ----------------------------------------------------------------------
# Core WAD Data Structures
# ----------------------------------------------------------------------

class WadEntry:
    def __init__(self, name, data, type_byte=0x44, cmprs=0):
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
            # Update name in the internal lump header (first 16 bytes)
            if len(entry.data) >= 16:
                name_bytes = new_name.encode('ascii', errors='ignore')[:15].ljust(16, b'\x00')
                entry.data = name_bytes + entry.data[16:]
            self.entries[new_name] = entry
            return True
        return False

    @classmethod
    def load(cls, filepath):
        if not os.path.exists(filepath):
            return cls()

        with open(filepath, 'rb') as f:
            header = f.read(12)
            if len(header) < 12:
                return cls()
            magic, numentries, diroffset = struct.unpack('<4sII', header)
            if magic not in (b'WAD2', b'WAD3'):
                raise ValueError(f"Invalid WAD magic: {magic.decode('ascii', errors='ignore')}")

            wad = cls(magic)
            f.seek(diroffset)
            dir_data = f.read(32 * numentries)
            
            entries_to_read = []
            for i in range(numentries):
                entry_bytes = dir_data[i*32 : (i+1)*32]
                if len(entry_bytes) < 32:
                    break
                offset, dsize, size, type_byte, cmprs, dummy, name_bytes = struct.unpack('<III2BH16s', entry_bytes)
                name = name_bytes.split(b'\x00')[0].decode('ascii', errors='ignore').lower()
                entries_to_read.append((offset, dsize, type_byte, cmprs, name))

            for offset, dsize, type_byte, cmprs, name in entries_to_read:
                f.seek(offset)
                data = f.read(dsize)
                wad.entries[name] = WadEntry(name, data, type_byte, cmprs)

        return wad

    def save(self, filepath):
        with open(filepath, 'wb') as f:
            # Write placeholder header
            f.write(struct.pack('<4sII', self.magic, 0, 0))
            
            offsets = {}
            for name, entry in self.entries.items():
                offset = f.tell()
                f.write(entry.data)
                offsets[name] = offset
            
            diroffset = f.tell()
            numentries = len(self.entries)
            
            for name, entry in self.entries.items():
                offset = offsets[name]
                dsize = len(entry.data)
                size = dsize
                type_byte = entry.type_byte
                cmprs = entry.cmprs
                dummy = 0
                name_bytes = name.encode('ascii', errors='ignore')[:15].ljust(16, b'\x00')
                
                entry_data = struct.pack('<III2BH16s', offset, dsize, size, type_byte, cmprs, dummy, name_bytes)
                f.write(entry_data)
                
            f.seek(0)
            f.write(struct.pack('<4sII', self.magic, numentries, diroffset))

# ----------------------------------------------------------------------
# BMP & Miptexture Compilation Utilities
# ----------------------------------------------------------------------

def sanitize_tex_name(filename):
    base = os.path.splitext(os.path.basename(filename))[0].lower()
    sanitized = re.sub(r'[^a-z0-9_]', '_', base)
    return sanitized[:15]

def compile_bmp_to_miptex(bmp_path, tex_name, wad_format="WAD2"):
    with Image.open(bmp_path) as img:
        w, h = img.size
        
        # New base-16 restriction check
        if w % 16 != 0 or h % 16 != 0:
            raise ValueError("Error : One or 2 values isn't divisible by 16")
            
        # Smart conversion based on target format
        if wad_format == "WAD2":
            has_q1_palette = False
            if img.mode == 'P':
                pal = img.getpalette()
                if pal and bytes(pal[:768]) == QUAKE_PALETTE:
                    has_q1_palette = True
            
            if not has_q1_palette:
                if img.mode == 'RGBA':
                    alpha = img.split()[-1]
                    rgb_img = img.convert('RGB')
                    palette_img = Image.new('P', (1, 1))
                    palette_img.putpalette(QUAKE_PALETTE)
                    quantized = rgb_img.quantize(palette=palette_img)
                    
                    pixels = bytearray(quantized.tobytes())
                    alpha_bytes = alpha.tobytes()
                    for idx in range(len(pixels)):
                        if alpha_bytes[idx] < 128:
                            pixels[idx] = 255
                    
                    img = Image.frombytes('P', img.size, bytes(pixels))
                    img.putpalette(QUAKE_PALETTE)
                else:
                    rgb_img = img.convert('RGB')
                    palette_img = Image.new('P', (1, 1))
                    palette_img.putpalette(QUAKE_PALETTE)
                    img = rgb_img.quantize(palette=palette_img)
        else:
            # WAD3 (Half-Life)
            if img.mode == 'RGBA':
                alpha = img.split()[-1]
                rgb_img = img.convert('RGB')
                # 255 colors leaves the last color (index 255) for transparency
                quantized = rgb_img.convert('P', palette=Image.Palette.ADAPTIVE, colors=255)
                
                pal = quantized.getpalette()
                if len(pal) < 765:
                    pal = pal + [0] * (765 - len(pal))
                pal = pal[:765] + [0, 0, 255] # Index 255 = blue
                
                pixels = bytearray(quantized.tobytes())
                alpha_bytes = alpha.tobytes()
                for idx in range(len(pixels)):
                    if alpha_bytes[idx] < 128:
                        pixels[idx] = 255
                
                img = Image.frombytes('P', img.size, bytes(pixels))
                img.putpalette(pal)
            elif img.mode != 'P':
                img = img.convert('P', palette=Image.Palette.ADAPTIVE, colors=256)
            
        # Generate 4 levels of mipmaps
        mips = [img]
        for i in range(1, 4):
            div = 2 ** i
            try:
                resampling = Image.Resampling.NEAREST
            except AttributeError:
                resampling = Image.NEAREST
            mip = img.resize((w // div, h // div), resampling)
            mips.append(mip)
            
        # Offsets relative to start of lump data (header is 40 bytes)
        offset0 = 40
        offset1 = offset0 + w * h
        offset2 = offset1 + (w // 2) * (h // 2)
        offset3 = offset2 + (w // 4) * (h // 4)
        
        # Pack header: '<16sII4I'
        name_bytes = tex_name.encode('ascii', errors='ignore')[:15].ljust(16, b'\x00')
        header = struct.pack('<16sII4I', name_bytes, w, h, offset0, offset1, offset2, offset3)
        
        pixel_data = bytearray()
        for mip in mips:
            pixel_data.extend(mip.tobytes())
            
        lump_data = header + pixel_data
        
        # Half-Life WAD3 appends the palette at the end
        if wad_format == "WAD3":
            palette = img.getpalette()
            if palette:
                if len(palette) < 768:
                    palette = palette + [0] * (768 - len(palette))
                palette_bytes = bytes(palette[:768])
                lump_data += struct.pack('<H', 256) + palette_bytes
                
        return lump_data

# ----------------------------------------------------------------------
# Quake 1 Standard Palette & Decoding Utilities
# ----------------------------------------------------------------------

QUAKE_PALETTE_HEX = "0000000f0f0f1f1f1f2f2f2f3f3f3f4b4b4b5b5b5b6b6b6b7b7b7b8b8b8b9b9b9babababbbbbbbcbcbcbdbdbdbebebeb0f0b07170f0b1f170b271b0f2f2313372b173f2f174b371b533b1b5b431f634b1f6b531f73571f7b5f238367238f6f230b0b0f13131b1b1b272727332f2f3f37374b3f3f574747674f4f735b5b7f63638b6b6b977373a37b7baf8383bb8b8bcb0000000707000b0b001313001b1b002323002b2b072f2f073737073f3f074747074b4b0b53530b5b5b0b63630b6b6b0f0700000f00001700001f00002700002f00003700003f00004700004f00005700005f00006700006f00007700007f00001313001b1b002323002f2b00372f004337004b3b075743075f47076b4b0b77530f8357138b5b13975f1ba3631faf67232313072f170b3b1f0f4b2313572b17632f1f7337237f3b2b8f43339f4f33af632fbf772fcf8f2bdfab27efcb1ffff31b0b07001b13002b230f372b1347331b533723633f2b6f47337f533f8b5f479b6b53a77b5fb7876bc3937bd3a38be3b397ab8ba39f7f979373878b677b7f5b6f7753636b4b575f3f4b5737434b2f3743272f371f232b171b231313170b0b0f0707bb739faf6b8fa35f839757778b4f6b7f4b5f7343536b3b4b5f333f532b3747232b3b1f232f171b231313170b0b0f0707dbc3bbcbb3a7bfa39baf978ba3877b977b6f876f5f7b63536b57475f4b3b533f33433327372b1f271f171b130f0f0b076f837b677b6f5f7367576b5f4f6357475b4f3f5347374b3f2f43372b3b2f2333271f2b1f1723170f1b130b130b070b07fff31befdf17dbcb13cbb70fbba70fab970b9b83078b73077b63076b53005b47004b37003b2b002b1f001b0f000b07000000ff0b0bef1313df1b1bcf2323bf2b2baf2f2f9f2f2f8f2f2f7f2f2f6f2f2f5f2b2b4f23233f1b1b2f13131f0b0b0f2b00003b00004b07005f07006f0f007f1707931f07a3270bb7330fc34b1bcf632bdb7f3be3974fe7ab5fefbf77f7d38ba77b3bb79b37c7c337e7e3577fbfffabe7ffd7ffff6700008b0000b30000d70000ff0000fff393fff7c7ffffff9f5b53"
QUAKE_PALETTE = bytes.fromhex(QUAKE_PALETTE_HEX)

def decode_miptex_to_image(lump_data, wad_format="WAD2"):
    if len(lump_data) < 40:
        raise ValueError("Lump data too short to contain miptexture header")
    name_bytes, w, h, off0, off1, off2, off3 = struct.unpack('<16sII4I', lump_data[:40])
    
    start = off0
    end = off0 + w * h
    if end > len(lump_data):
        raise ValueError(f"Miptexture pixel data offset exceeds lump size: {end} > {len(lump_data)}")
    
    pixel_data = lump_data[start:end]
    
    if wad_format == "WAD3":
        if len(lump_data) >= end + 2 + 768:
            palette_bytes = lump_data[-768:]
        else:
            palette_bytes = QUAKE_PALETTE
    else:
        palette_bytes = QUAKE_PALETTE
        
    img = Image.frombytes('P', (w, h), pixel_data)
    img.putpalette(palette_bytes)
    return img

# ----------------------------------------------------------------------
# Business-Logic Operations
# ----------------------------------------------------------------------

def scan_workspace_bmps(folder):
    """Scan a workspace folder for image files, analyze them, and detect
    duplicates/conflicts. Returns a list of file-info dicts."""
    if not os.path.exists(folder):
        raise FileNotFoundError(f"Workspace directory does not exist: {folder}")
    
    valid_extensions = (".bmp", ".png", ".tga", ".pcx", ".jpg", ".jpeg", ".gif", ".tiff", ".tif")
    
    bmp_files = []
    for f in os.listdir(folder):
        if f.lower().endswith(valid_extensions):
            bmp_files.append(f)
    
    if not bmp_files:
        return []
    
    detected_bmps = []
    hash_to_files = {}
    name_to_files = {}
    
    for f_name in bmp_files:
        full_path = os.path.join(folder, f_name)
        tex_name = sanitize_tex_name(f_name)
        
        file_info = {
            "filename": f_name,
            "texname": tex_name,
            "res": "Unknown",
            "format": "Unknown",
            "status": "OK",
            "valid": True,
            "path": full_path
        }
        
        try:
            with Image.open(full_path) as img:
                w, h = img.size
                file_info["res"] = f"{w}x{h}"
                file_info["format"] = img.mode
                
                if w % 16 != 0 or h % 16 != 0:
                    file_info["status"] = "Error : One or 2 values isn't divisible by 16"
                    file_info["valid"] = False
                elif img.mode not in ('P', '1'):
                    file_info["status"] = "WARN: RGB Mode"
                
                try:
                    pixel_bytes = img.tobytes()
                    pixel_hash = hashlib.md5(pixel_bytes).hexdigest()
                    file_info["hash"] = pixel_hash
                    
                    if pixel_hash not in hash_to_files:
                        hash_to_files[pixel_hash] = []
                    hash_to_files[pixel_hash].append(f_name)
                except Exception:
                    file_info["hash"] = None
        except Exception as e:
            file_info["status"] = f"ERR: Can't read ({str(e)[:20]})"
            file_info["valid"] = False
            
        if tex_name not in name_to_files:
            name_to_files[tex_name] = []
        name_to_files[tex_name].append(f_name)
        
        detected_bmps.append(file_info)
    
    warnings = []
    for info in detected_bmps:
        t_name = info["texname"]
        if len(name_to_files[t_name]) > 1:
            conflicting = [f for f in name_to_files[t_name] if f != info["filename"]]
            info["status"] = f"CONFLICT: Name shares '{t_name}'"
            warnings.append(("warning", f"Texture name conflict: File '{info['filename']}' maps to the same name '{t_name}' as {conflicting}"))
            
        elif "hash" in info and info["hash"]:
            p_hash = info["hash"]
            if len(hash_to_files[p_hash]) > 1:
                first_file = hash_to_files[p_hash][0]
                if first_file != info["filename"]:
                    info["status"] = f"DUP: Content same as '{first_file}'"
                    warnings.append(("info", f"Content duplicate: File '{info['filename']}' has identical pixels to '{first_file}'"))
    
    return detected_bmps, warnings


def read_wad_contents(wad_path):
    wad = WadFile.load(wad_path)
    loaded_format = wad.magic.decode('ascii', errors='ignore')
    
    entries_list = []
    for name, entry in sorted(wad.entries.items()):
        res_str = "Unknown"
        if entry.type_byte in (0x43, 0x44) and len(entry.data) >= 24:
            try:
                _, w, h = struct.unpack('<16sII', entry.data[:24])
                res_str = f"{w}x{h}"
            except Exception:
                pass
        entries_list.append({
            "name": name,
            "res": res_str,
            "size": len(entry.data)
        })
    
    return loaded_format, entries_list


def rename_workspace_file(workspace, old_name, new_name):
    old_path = os.path.join(workspace, old_name)
    if not os.path.exists(old_path):
        raise FileNotFoundError(f"File '{old_name}' not found in workspace")
    
    _, ext = os.path.splitext(old_name.lower())
    if not new_name.lower().endswith(ext):
        new_name += ext
    
    new_path = os.path.join(workspace, new_name)
    if os.path.exists(new_path):
        raise FileExistsError("A file with this name already exists.")
    
    os.rename(old_path, new_path)
    return new_name


def rename_wad_entry(wad_path, old_name, new_name):
    new_name = sanitize_tex_name(new_name)
    if not new_name:
        raise ValueError("Invalid texture name.")
    
    wad = WadFile.load(wad_path)
    if new_name in wad.entries and new_name != old_name:
        raise ValueError(f"Texture '{new_name}' already exists in this WAD.")
    
    if wad.rename_entry(old_name, new_name):
        wad.save(wad_path)
        return new_name
    else:
        raise KeyError(f"Entry '{old_name}' not found in WAD")


def delete_workspace_files(workspace, filenames):
    success = 0
    errors = []
    for fname in filenames:
        path = os.path.join(workspace, fname)
        try:
            if os.path.exists(path):
                os.remove(path)
                success += 1
        except Exception as e:
            errors.append((fname, str(e)))
    return success, errors


def delete_wad_entries(wad_path, names):
    wad = WadFile.load(wad_path)
    success = 0
    for name in names:
        if wad.delete_entry(name):
            success += 1
    wad.save(wad_path)
    return success


def export_wad_entry(wad_path, entry_name, dest_path, wad_format):
    wad = WadFile.load(wad_path)
    if entry_name not in wad.entries:
        raise KeyError(f"Entry '{entry_name}' not found in WAD")
    img = decode_miptex_to_image(wad.entries[entry_name].data, wad_format)
    img.save(dest_path)


def export_wad_entries_bulk(wad_path, names, dest_dir, wad_format):
    wad = WadFile.load(wad_path)
    success = 0
    for name in names:
        if name in wad.entries:
            img = decode_miptex_to_image(wad.entries[name].data, wad_format)
            dest_path = os.path.join(dest_dir, f"{name}.bmp")
            img.save(dest_path)
            success += 1
    return success


def replace_wad_entry(wad_path, entry_name, bmp_path, wad_format):
    with Image.open(bmp_path) as img:
        w, h = img.size
        if w % 16 != 0 or h % 16 != 0:
            raise ValueError("Error : One or 2 values isn't divisible by 16")
    
    lump_data = compile_bmp_to_miptex(bmp_path, entry_name, wad_format)
    
    wad = WadFile.load(wad_path)
    type_byte = 0x43 if wad_format == "WAD3" else 0x44
    wad.add_entry(WadEntry(entry_name, lump_data, type_byte=type_byte))
    wad.save(wad_path)


def convert_wad_format_file(wad_path, current_format, target_format):
    wad = WadFile.load(wad_path)
    wad.magic = target_format.encode('ascii')
    type_byte = 0x43 if target_format == "WAD3" else 0x44
    
    success = 0
    for name, entry in list(wad.entries.items()):
        entry.type_byte = type_byte
        if target_format == "WAD3":
            if len(entry.data) >= 40:
                _, w, h = struct.unpack('<16sII', entry.data[:24])
                pixel_data_size = (w * h * 85) // 64
                if len(entry.data) < 40 + pixel_data_size + 768:
                    palette_data = struct.pack('<H', 256) + QUAKE_PALETTE
                    entry.data = entry.data + palette_data
                    success += 1
        else:
            if len(entry.data) >= 40:
                _, w, h = struct.unpack('<16sII', entry.data[:24])
                pixel_data_size = (w * h * 85) // 64
                expected_wad2_size = 40 + pixel_data_size
                if len(entry.data) > expected_wad2_size:
                    entry.data = entry.data[:expected_wad2_size]
                    success += 1
                    
    wad.save(wad_path)
    return success


def pack_textures_to_wad(wad_path, to_pack, wad_format, progress_cb=None):
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
            lump_data = compile_bmp_to_miptex(info["path"], info["texname"], wad_format)
            entry = WadEntry(info["texname"], lump_data, type_byte=type_byte)
            wad.add_entry(entry)
            success_count += 1
            if progress_cb:
                progress_cb(i + 1, total, f"Successfully compiled '{info['texname']}' ({info['res']})", "success")
        except Exception as e:
            if progress_cb:
                progress_cb(i + 1, total, f"Failed to compile '{info['filename']}': {str(e)}", "error")
    
    if success_count > 0:
        if progress_cb:
            progress_cb(total, total, f"Saving WAD file: {os.path.basename(wad_path)}...", "info")
        wad.save(wad_path)
    
    return success_count