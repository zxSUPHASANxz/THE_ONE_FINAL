#!/usr/bin/env python3
"""
Helper to install THE_ONE logo and create a 32x32 favicon.

Usage:
  python scripts/add_logo.py --src uploads/the_one_source.png

If the `uploads` folder contains the source image (for example from a chat attachment),
this script copies it to `static/images/the_one_logo.png` and also writes
`static/images/the_one_favicon.png` resized to 32x32.

Requires: Pillow (`pip install pillow`)
"""
import argparse
import os
from PIL import Image


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def install_logo(src_path: str, dest_dir: str = "static/images"):
    ensure_dir(dest_dir)
    logo_dest = os.path.join(dest_dir, "the_one_logo.png")
    favicon_dest = os.path.join(dest_dir, "the_one_favicon.png")

    if not os.path.isfile(src_path):
        raise FileNotFoundError(f"Source image not found: {src_path}")

    with Image.open(src_path) as img:
        # Save main logo (convert to RGBA to preserve transparency)
        logo = img.convert("RGBA")
        logo.save(logo_dest, format="PNG")

        # Create favicon (32x32)
        fav = logo.copy()
        fav.thumbnail((32, 32), Image.LANCZOS)
        # Ensure exact size 32x32 by pasting onto transparent background if needed
        if fav.size != (32, 32):
            canvas = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
            x = (32 - fav.width) // 2
            y = (32 - fav.height) // 2
            canvas.paste(fav, (x, y), fav)
            canvas.save(favicon_dest, format="PNG")
        else:
            fav.save(favicon_dest, format="PNG")

    return logo_dest, favicon_dest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", required=True, help="Path to source image (PNG/JPEG)")
    parser.add_argument("--dest", default="static/images", help="Destination images directory")
    args = parser.parse_args()

    try:
        logo, favicon = install_logo(args.src, args.dest)
        print(f"Installed logo: {logo}")
        print(f"Installed favicon: {favicon}")
    except Exception as e:
        print("Error:", e)
        raise


if __name__ == "__main__":
    main()
