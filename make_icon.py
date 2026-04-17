# -*- coding: utf-8 -*-
"""NaverBlogAuto 아이콘 생성"""
from PIL import Image, ImageDraw, ImageFont
import os

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(img)

# 배경: 네이버 녹색 그라디언트 (라운드 사각형)
r = 48  # 라운드 반지름
for y in range(SIZE):
    t = y / SIZE
    # 위(#03C75A) → 아래(#019640)
    rc = int(0x03 + (0x01 - 0x03) * t)
    gc = int(0xC7 + (0x96 - 0xC7) * t)
    bc = int(0x5A + (0x40 - 0x5A) * t)
    d.line([(0, y), (SIZE, y)], fill=(rc, gc, bc, 255))

# 라운드 사각 마스크
mask = Image.new("L", (SIZE, SIZE), 0)
dm = ImageDraw.Draw(mask)
dm.rounded_rectangle((0, 0, SIZE - 1, SIZE - 1), radius=r, fill=255)
bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
bg.paste(img, (0, 0), mask)

# 내용 그리기 — 연필 + B 문자 스타일
d2 = ImageDraw.Draw(bg)

# 흰색 둥근 사각 카드 (블로그 페이지 느낌)
card_pad = 50
card = (card_pad, card_pad + 10, SIZE - card_pad, SIZE - card_pad + 10)
d2.rounded_rectangle(card, radius=18, fill=(255, 255, 255, 230))

# 글 라인 (회색 3줄)
line_color = (130, 130, 130, 255)
line_x0 = card_pad + 20
line_x1 = SIZE - card_pad - 20
y0 = card_pad + 36
for i in range(4):
    w = int((line_x1 - line_x0) * (1.0 - 0.15 * i))
    d2.rounded_rectangle((line_x0, y0 + i * 24, line_x0 + w, y0 + i * 24 + 10), radius=4, fill=line_color)

# 우측 상단에 녹색 "N" 배지
badge_r = 36
cx = SIZE - 50
cy = 58
d2.ellipse((cx - badge_r, cy - badge_r, cx + badge_r, cy + badge_r), fill=(3, 199, 90, 255))

# "N" 글자
try:
    font = ImageFont.truetype("arialbd.ttf", 48)
except Exception:
    font = ImageFont.load_default()
text = "N"
bbox = d2.textbbox((0, 0), text, font=font)
tw = bbox[2] - bbox[0]
th = bbox[3] - bbox[1]
d2.text((cx - tw / 2 - bbox[0], cy - th / 2 - bbox[1]), text, fill=(255, 255, 255, 255), font=font)

out_path = os.path.join(os.path.dirname(__file__), "icon.ico")
bg.save(out_path, format="ICO", sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(f"Saved: {out_path}")
