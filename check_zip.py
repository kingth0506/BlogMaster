import zipfile
with zipfile.ZipFile('dist/BlogMaster_files.zip') as z:
    names = z.namelist()
    print('총', len(names), '개 파일')
    for n in names[:5]:
        print(' ', n)
    print('  ...')
    exes = [n for n in names if n.endswith('.exe')]
    print('exe 파일:', exes[:3])
