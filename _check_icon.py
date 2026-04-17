from PIL import Image
i = Image.open('icon.ico')
print('sizes:', i.info.get('sizes'))
print('size:', i.size)
print('format:', i.format)
