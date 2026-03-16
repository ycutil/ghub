import zipfile
import os

src = r"C:\Users\Administrator\Documents\aion\ghub\dist\release_pkg"
out = r"C:\Users\Administrator\Documents\aion\ghub\dist\aion_ghub_v1.6.0.zip"

with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk(src):
        for f in files:
            full = os.path.join(root, f)
            arc = os.path.relpath(full, src)
            z.write(full, arc)
            print(f"  + {arc}")

print(f"\n완료: {out}")
