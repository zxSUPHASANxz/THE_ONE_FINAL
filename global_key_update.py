
import os
import glob

import argparse

# Do NOT hard-code keys here. Accept via environment or args.
NEW_KEY = os.getenv("NEW_GEMINI_KEY")
OLD_KEY = os.getenv("OLD_GEMINI_KEY")

# Allow command-line overrides for batch updates
parser = argparse.ArgumentParser(description='Update API keys in repository files')
parser.add_argument('--old', dest='old', help='Old key to replace')
parser.add_argument('--new', dest='new', help='New key to write')
args = parser.parse_args()
if args.old:
    OLD_KEY = args.old
if args.new:
    NEW_KEY = args.new

if not NEW_KEY or not OLD_KEY:
    print("ERROR: NEW_GEMINI_KEY and OLD_GEMINI_KEY must be provided via env or --old/--new args")
    raise SystemExit(1)

FILES_TO_CHECK = [
    ".env",
    "start_ngrok.ps1",
    "quick_start.ps1",
    "fix_database.bat",
    "debug_pgvector.py",
    "scraper_and_import_embedding/detailed_scrapers/honda_full_auto_scraper.py",
    "scraper_and_import_embedding/detailed_scrapers/honda_auto_scraper.py"
]

def update_file(filepath):
    if not os.path.exists(filepath):
        print(f"Skipping {filepath} (not found)")
        return

    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        updated = False
        
        # Specific handling for .env to ensure we don't just replace but ensure the key is correct
        if filepath == ".env":
            lines = content.splitlines()
            new_lines = []
            found_env = False
            for line in lines:
                if line.strip().startswith("GEMINI_API_KEY="):
                    new_lines.append(f"GEMINI_API_KEY={NEW_KEY}")
                    found_env = True
                    updated = True
                else:
                    new_lines.append(line)
            if not found_env:
                new_lines.append(f"GEMINI_API_KEY={NEW_KEY}")
                updated = True
            content = "\n".join(new_lines)
            if lines and not lines[-1].endswith('\n') and not content.endswith('\n'):
                 content += '\n' # Ensure EOF newline if preferred, though join might need care.
            
        else:
            # For other files, simple string replacement
            if OLD_KEY in content:
                content = content.replace(OLD_KEY, NEW_KEY)
                updated = True
        
        if updated:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"Updated {filepath}")
        else:
            print(f"No changes needed for {filepath}")

    except Exception as e:
        print(f"Error updating {filepath}: {e}")

if __name__ == "__main__":
    base_dir = os.getcwd()
    print(f"Scanning from {base_dir}")
    for file_rel_path in FILES_TO_CHECK:
        full_path = os.path.join(base_dir, file_rel_path.replace('/', os.sep))
        update_file(full_path)
