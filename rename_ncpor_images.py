import os

# CHANGE THIS IF NEEDED
FOLDER = r"static/images/ncpor"
PREFIX = "ncpor_"

# Get all image files
files = [
    f for f in os.listdir(FOLDER)
    if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))
]

# Sort for consistent order
files.sort()

# Rename
for i, filename in enumerate(files, start=1):
    ext = os.path.splitext(filename)[1]
    new_name = f"{PREFIX}{i:02d}{ext}"

    old_path = os.path.join(FOLDER, filename)
    new_path = os.path.join(FOLDER, new_name)

    if old_path != new_path:
        os.rename(old_path, new_path)
        print(f"[✓] {filename} → {new_name}")

print("\nDone. Images renamed successfully.")
