import re
import sys
import os

# Global registry to track every single ID across all processed files
used_ids = set()

def text_to_slug(text):
    """Converts raw header text into a standard lowercase underscore base slug."""
    slug_base = text.lower().strip()
    # Convert hyphens to spaces first so they act as proper word separators
    slug_base = re.sub(r'-', ' ', slug_base)
    # Remove common inline formatting like *bold* or _italics_
    slug_base = re.sub(r'[*_`\']', '', slug_base)
    # Replace non-alphanumeric characters (except spaces) with nothing
    slug_base = re.sub(r'[^a-z0-9\s]', '', slug_base)
    # Replace spaces with a single underscore
    slug_base = re.sub(r'\s+', '_', slug_base)
    return f"_{slug_base}" if slug_base else "_header"

def ensure_unique(id_str):
    """Checks if an ID is taken. If it is, increments it cleanly (_rke -> _rke_1)."""
    if id_str not in used_ids:
        used_ids.add(id_str)
        return id_str
    
    match = re.match(r'^(.*)_(\d+)$', id_str)
    if match:
        base = match.group(1)
        counter = int(match.group(2))
    else:
        base = id_str
        counter = 1
        
    while True:
        candidate = f"{base}_{counter}"
        if candidate not in used_ids:
            used_ids.add(candidate)
            return candidate
        counter += 1

def anchor_english_file(file_path):
    """Ensures every H2+ header in the English file has a globally unique ID."""
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    modified_lines = []
    in_code_block = False
    changes_made = 0
    
    for line in lines:
        if re.match(r'^([-]{4,}|\.{4,})$', line.strip()):
            in_code_block = not in_code_block
            
        header_match = re.match(r'^([=]{2,6})\s+(.+)$', line.rstrip())
        if header_match and not in_code_block:
            header_text = header_match.group(2)
            
            has_existing_id = (len(modified_lines) > 0 and re.match(r'^\[#([^\]]+)\]$', modified_lines[-1].strip()))
            
            if has_existing_id:
                existing_id_value = re.match(r'^\[#([^\]]+)\]$', modified_lines[-1].strip()).group(1)
                unique_id = ensure_unique(existing_id_value)
                
                if unique_id != existing_id_value:
                    modified_lines[-1] = f"[#{unique_id}]\n"
                    changes_made += 1
            else:
                slug_base = text_to_slug(header_text)
                unique_id = ensure_unique(slug_base)
                modified_lines.append(f"[#{unique_id}]\n")
                changes_made += 1
                
        modified_lines.append(line)
    
    if changes_made > 0:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
        print(f"✓ Processed English file ({changes_made} ID updates/additions): {os.path.basename(file_path)}")

def get_english_ids(en_file_path):
    """Reads the final, guaranteed-unique IDs sequentially from an English file."""
    en_ids = []
    with open(en_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    in_code_block = False
    for i, line in enumerate(lines):
        if re.match(r'^([-]{4,}|\.{4,})$', line.strip()):
            in_code_block = not in_code_block
            continue
        header_match = re.match(r'^([=]{2,6})\s+(.+)$', line.rstrip())
        if header_match and not in_code_block:
            id_match = None
            if i > 0:
                id_match = re.match(r'^\[#([^\]]+)\]$', lines[i-1].strip())
            en_ids.append(id_match.group(1) if id_match else "unknown")
    return en_ids

def process_translated_file(en_file_path, target_file_path):
    """Maps the precise English IDs directly onto the translated file."""
    en_ids = get_english_ids(en_file_path)
    with open(target_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    target_header_count = 0
    in_code_block = False
    for line in lines:
        if re.match(r'^([-]{4,}|\.{4,})$', line.strip()):
            in_code_block = not in_code_block
            continue
        if re.match(r'^([=]{2,6})\s+(.+)$', line.rstrip()) and not in_code_block:
            target_header_count += 1

    if target_header_count != len(en_ids):
        print(f"❌ Skipping {os.path.basename(target_file_path)}: Header count mismatch (EN has {len(en_ids)}, Target has {target_header_count}).")
        return

    modified_lines = []
    in_code_block = False
    id_index = 0
    changes_made = 0
    
    for line in lines:
        if re.match(r'^([-]{4,}|\.{4,})$', line.strip()):
            in_code_block = not in_code_block
            
        header_match = re.match(r'^([=]{2,6})\s+(.+)$', line.rstrip())
        if header_match and not in_code_block:
            has_id = (len(modified_lines) > 0 and re.match(r'^\[#([^\]]+)\]$', modified_lines[-1].strip()))
            expected_id = en_ids[id_index]
            
            if has_id:
                existing_target_id = re.match(r'^\[#([^\]]+)\]$', modified_lines[-1].strip()).group(1)
                if existing_target_id != expected_id:
                    modified_lines[-1] = f"[#{expected_id}]\n"
                    changes_made += 1
            else:
                modified_lines.append(f"[#{expected_id}]\n")
                changes_made += 1
            id_index += 1
            
        modified_lines.append(line)
        
    if changes_made > 0:
        with open(target_file_path, 'w', encoding='utf-8') as f:
            f.writelines(modified_lines)
        print(f"✓ Synced {changes_made} updated IDs to translation: {os.path.basename(target_file_path)}")

if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 1 or len(args) > 2:
        print("Usage:")
        print("  Update English only:   python3 sync_headers_batch.py <en_path>")
        print("  Update EN & Sync Target: python3 sync_headers_batch.py <en_path> <target_path>")
        sys.exit(1)

    en_base = args[0]
    target_base = args[1] if len(args) == 2 else None
    
    if not os.path.isdir(en_base):
        print(f"❌ Error: English directory path does not exist or is not a folder: '{en_base}'")
        sys.exit(1)

    print("Phase 1: Structuring and resolving duplicates in English source files...")
    for root, _, files in os.walk(en_base):
        for file in files:
            if file == 'nav.adoc' or not file.lower().endswith('.adoc'): 
                continue
            anchor_english_file(os.path.join(root, file))

    if target_base:
        if not os.path.isdir(target_base):
            print(f"❌ Error: Target directory path does not exist or is not a folder: '{target_base}'")
            sys.exit(1)

        print("\nPhase 2: Syncing unique IDs to translation files...")
        for root, _, files in os.walk(en_base):
            for file in files:
                if file == 'nav.adoc' or not file.lower().endswith('.adoc'): 
                    continue
                en_path = os.path.join(root, file)
                rel_path = os.path.relpath(en_path, en_base)
                target_path = os.path.join(target_base, rel_path)
                
                if os.path.exists(target_path):
                    process_translated_file(en_path, target_path)
    else:
        print("\nSkipping Phase 2: No translation target path provided.")