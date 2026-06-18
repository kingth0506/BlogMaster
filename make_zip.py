import zipfile, os
dist_dir = 'dist/BlogMaster'
zip_path = 'dist/BlogMaster_files.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(dist_dir):
        for file in files:
            fp = os.path.join(root, file)
            arcname = os.path.relpath(fp, dist_dir)
            zf.write(fp, arcname)
print('zip done:', os.path.getsize(zip_path), 'bytes')
