
import os
import glob

NEW_KEY = "AIzaSyDu2sGMNZPdAIhZUp0tsZ_7DrKDPqhwhtY"
OLD_KEY = "AIzaSyCUG68eKoNRGDWDEd7p6ZIGQHOVjVIUvtU"

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
