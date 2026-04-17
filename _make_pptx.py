# -*- coding: utf-8 -*-
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import os

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

BG = RGBColor(0x1e, 0x29, 0x3b)
WHITE = RGBColor(0xff, 0xff, 0xff)
BLUE = RGBColor(0x4a, 0x6c, 0xf7)
GREEN = RGBColor(0x22, 0xc5, 0x5e)
GRAY = RGBColor(0x94, 0xa3, 0xb8)
RED = RGBColor(0xef, 0x44, 0x44)

def set_bg(slide):
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = BG

def add_text(slide, left, top, width, height, text, size=18, bold=False, color=WHITE, align=PP_ALIGN.LEFT):
    txBox = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.alignment = align
    return tf

def add_para(tf, text, size=16, bold=False, color=WHITE, bullet=False):
    p = tf.add_paragraph()
    p.text = ("\u2022  " + text) if bullet else text
    p.font.size = Pt(size)
    p.font.bold = bold
    p.font.color.rgb = color
    p.space_before = Pt(6)

# 표지
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 1, 1.5, 11, 1.5, "BlogMaster", 54, True, BLUE, PP_ALIGN.CENTER)
add_text(slide, 1, 3.2, 11, 1, "\ub124\uc774\ubc84 \ud50c\ub808\uc774\uc2a4 \ube14\ub85c\uadf8 \uc790\ub3d9 \ud3ec\uc2a4\ud305", 28, False, WHITE, PP_ALIGN.CENTER)
add_text(slide, 1, 4.5, 11, 0.8, "\uc0ac\uc6a9 \uc124\uba85\uc11c", 22, False, GRAY, PP_ALIGN.CENTER)
add_text(slide, 1, 5.5, 11, 0.6, "2026\ub144 4\uc6d4", 16, False, GRAY, PP_ALIGN.CENTER)

# 목차
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 5, 0.8, "\ubaa9\ucc28", 36, True, BLUE)
tf = add_text(slide, 1, 1.5, 10, 5.5, "", 20)
for item in ["1.  \ud504\ub85c\uadf8\ub7a8 \uc124\uce58", "2.  \ub85c\uadf8\uc778", "3.  \uba54\uc778 \ud654\uba74 \uad6c\uc131",
             "4.  \ud06c\ub864\ub9c1 (F5)", "5.  \ud3ec\uc2a4\ud2b8 \uc0dd\uc131 (F7)", "6.  \uc790\ub3d9 \ud3ec\uc2a4\ud305 (F8)",
             "7.  \ud504\ub86c\ud504\ud2b8 \ud3b8\uc9d1", "8.  \uc124\uc815", "9.  \ub2e8\ucd95\ud0a4", "10. \uc8fc\uc758\uc0ac\ud56d"]:
    add_para(tf, item, 22, color=WHITE)

# 1. 설치
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "1. \ud504\ub85c\uadf8\ub7a8 \uc124\uce58", 36, True, BLUE)
tf = add_text(slide, 1, 1.8, 11, 5, "", 20)
add_para(tf, "NaverBlogAuto_Install.exe \uc2e4\ud589", 22, color=WHITE, bullet=True)
add_para(tf, "\uc124\uce58 \uacbd\ub85c \uc9c0\uc815 \u2192 \uc124\uce58 \uc644\ub8cc", 22, color=WHITE, bullet=True)
add_para(tf, "\ubc14\ud0d5\ud654\uba74\uc5d0 NaverBlogAuto \uc544\uc774\ucf58 \uc0dd\uc131", 22, color=WHITE, bullet=True)
add_para(tf, "", 14)
add_para(tf, "\u203b Chrome \ube0c\ub77c\uc6b0\uc800\uac00 \uc124\uce58\ub418\uc5b4 \uc788\uc5b4\uc57c \ud569\ub2c8\ub2e4", 18, color=GRAY)

# 2. 로그인
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "2. \ub85c\uadf8\uc778", 36, True, BLUE)
tf = add_text(slide, 1, 1.8, 11, 5, "", 20)
add_para(tf, "\ud504\ub85c\uadf8\ub7a8 \uc2e4\ud589 \uc2dc \ub85c\uadf8\uc778 \ucc3d\uc774 \ub098\ud0c0\ub0a9\ub2c8\ub2e4", 22, color=WHITE)
add_para(tf, "", 10)
add_para(tf, "\uc544\uc774\ub514\uc640 \ube44\ubc00\ubc88\ud638 \uc785\ub825 \ud6c4 \ub85c\uadf8\uc778", 22, color=WHITE, bullet=True)
add_para(tf, "\uc0ac\uc6a9 \uae30\uac04 \ub0b4\uc5d0\ub9cc \ub85c\uadf8\uc778 \uac00\ub2a5", 22, color=WHITE, bullet=True)
add_para(tf, "\uc544\uc774\ub514/\ube44\ubc00\ubc88\ud638 \uc800\uc7a5 \uae30\ub2a5 \uc9c0\uc6d0", 22, color=WHITE, bullet=True)

# 3. 메인 화면
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "3. \uba54\uc778 \ud654\uba74", 36, True, BLUE)
add_text(slide, 0.8, 1.5, 5, 0.6, "\uc88c\uce21 \ud328\ub110", 24, True, GREEN)
tf = add_text(slide, 1, 2.3, 5.5, 4, "", 18)
add_para(tf, "\ud0a4\uc6cc\ub4dc \uc785\ub825 (\uc9c0\uc5ed+\uc5c5\uc885)", 18, color=WHITE, bullet=True)
add_para(tf, "\ud06c\ub864\ub9c1 \uc2dc\uc791 (F5) / \uc911\ub2e8 (F6)", 18, color=WHITE, bullet=True)
add_para(tf, "\ud3ec\uc2a4\ud2b8 \uc0dd\uc131 (F7)", 18, color=WHITE, bullet=True)
add_para(tf, "\ud3ec\uc2a4\ud2b8 \ubcf4\uae30 \ubc0f \ud3ec\uc2a4\ud305 (F8)", 18, color=WHITE, bullet=True)
add_para(tf, "\ud06c\ub864\ub9c1 \uacb0\uacfc\ubcf4\uae30", 18, color=WHITE, bullet=True)

add_text(slide, 7, 1.5, 5, 0.6, "\uc6b0\uce21 \ud328\ub110", 24, True, GREEN)
tf2 = add_text(slide, 7.2, 2.3, 5.5, 4, "", 18)
add_para(tf2, "\uacc4\uc815 \uc120\ud0dd (1~9\ubc88)", 18, color=WHITE, bullet=True)
add_para(tf2, "\ub300\uc2dc\ubcf4\ub4dc (\uc791\uc131 \uc218, API \uc0ac\uc6a9\ub7c9)", 18, color=WHITE, bullet=True)
add_para(tf2, "\uc2e4\ud589 \ub85c\uadf8 (\uc2e4\uc2dc\uac04 \uc9c4\ud589 \uc0c1\ud669)", 18, color=WHITE, bullet=True)

# 4. 크롤링
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "4. \ud06c\ub864\ub9c1 (F5)", 36, True, BLUE)
tf = add_text(slide, 1, 1.8, 11, 5, "", 20)
add_para(tf, "\ub124\uc774\ubc84 \ud50c\ub808\uc774\uc2a4\uc5d0\uc11c \uc5c5\uccb4 \uc815\ubcf4\ub97c \uc790\ub3d9 \uc218\uc9d1\ud569\ub2c8\ub2e4", 22, color=WHITE)
add_para(tf, "", 10)
add_para(tf, "\ud0a4\uc6cc\ub4dc \uc785\ub825: \"\uc911\ub791\uad6c\uc694\uc591\uc6d0\", \"\uac15\uc11c\uad6c\ud5ec\uc2a4\uc7a5\" \ud615\ud0dc", 20, color=WHITE, bullet=True)
add_para(tf, "\uc218\uc9d1 \uac1c\uc218 \uc124\uc815 (\uae30\ubcf8 100\uac1c)", 20, color=WHITE, bullet=True)
add_para(tf, "F5 \ub610\ub294 \ud06c\ub864\ub9c1 \uc2dc\uc791 \ubc84\ud2bc \ud074\ub9ad", 20, color=WHITE, bullet=True)
add_para(tf, "", 10)
add_para(tf, "\uc218\uc9d1 \uc815\ubcf4: \uc5c5\uccb4\uba85, \uc8fc\uc18c, \uce74\ud14c\uace0\ub9ac, \uadfc\ucc98\uc5ed, \ud0dc\uadf8 \ub4f1", 18, color=GRAY)

# 5. 포스트 생성
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "5. \ud3ec\uc2a4\ud2b8 \uc0dd\uc131 (F7)", 36, True, BLUE)
tf = add_text(slide, 1, 1.8, 5.5, 5, "", 20)
add_para(tf, "\ud06c\ub864\ub9c1\ub41c \uc5c5\uccb4 \uc120\ud0dd \u2192 AI\uac00 \uc790\ub3d9 \uc0dd\uc131", 20, color=WHITE)
add_para(tf, "", 10)
add_para(tf, "F7 \ud074\ub9ad \u2192 \uc5c5\uccb4 \uccb4\ud06c \u2192 \ud3ec\uc2a4\ud2b8 \uc0dd\uc131", 20, color=WHITE, bullet=True)
add_para(tf, "GPT / Gemini \uc120\ud0dd \uac00\ub2a5", 20, color=WHITE, bullet=True)
add_para(tf, "\ubcf8\ubb38 + \uc81c\ubaa9 + \ud0dc\uadf8 \uc790\ub3d9 \uc0dd\uc131", 20, color=WHITE, bullet=True)
add_para(tf, "\uc774\ubbf8\uc9c0 Pixabay\uc5d0\uc11c \uc790\ub3d9 \ub2e4\uc6b4\ub85c\ub4dc", 20, color=WHITE, bullet=True)

add_text(slide, 7, 1.5, 5, 0.6, "\uc0c1\ud0dc \ud45c\uc2dc", 24, True, GREEN)
tf2 = add_text(slide, 7.2, 2.3, 5, 3, "", 20)
add_para(tf2, "\ube68\uac04\uc0c9 \u25cf  \ubbf8\uc0dd\uc131", 22, color=RED)
add_para(tf2, "\ucd08\ub85d\uc0c9 \u25cf  \uc0dd\uc131 \uc644\ub8cc", 22, color=GREEN)
add_para(tf2, "[\uc644]  \ud3ec\uc2a4\ud305 \uc644\ub8cc", 22, color=BLUE)

# 6. 포스팅
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "6. \uc790\ub3d9 \ud3ec\uc2a4\ud305 (F8)", 36, True, BLUE)
tf = add_text(slide, 1, 1.8, 5.5, 5, "", 20)
add_para(tf, "\uc0dd\uc131\ub41c \ud3ec\uc2a4\ud2b8\ub97c \ub124\uc774\ubc84 \ube14\ub85c\uadf8\uc5d0 \uc790\ub3d9 \uc5c5\ub85c\ub4dc", 20, color=WHITE)
add_para(tf, "", 10)
add_para(tf, "F8 \ud074\ub9ad \u2192 \ud56d\ubaa9 \uccb4\ud06c \u2192 \uc790\ub3d9 \ud3ec\uc2a4\ud305", 20, color=WHITE, bullet=True)
add_para(tf, "\ubc1c\ud589 \uac04\uaca9 \uc124\uc815 (\uc608: 2\uc2dc\uac04)", 20, color=WHITE, bullet=True)
add_para(tf, "\uccab \ud3ec\uc2a4\ud2b8 \uc989\uc2dc/\ub300\uae30 \uc635\uc158", 20, color=WHITE, bullet=True)

add_text(slide, 7, 1.5, 5, 0.6, "\ubc1c\ud589 \ubc29\uc2dd", 24, True, GREEN)
tf2 = add_text(slide, 7.2, 2.3, 5, 3, "", 20)
add_para(tf2, "\uc989\uc2dc \ubc1c\ud589: \uccab \ubc88\uc9f8 \ud3ec\uc2a4\ud2b8", 20, color=WHITE, bullet=True)
add_para(tf2, "\uc608\uc57d \ubc1c\ud589: 2\ubc88\uc9f8\ubd80\ud130 \uac04\uaca9 \uc801\uc6a9", 20, color=WHITE, bullet=True)
add_para(tf2, "\uce74\ud14c\uace0\ub9ac + \ud0dc\uadf8 \uc790\ub3d9 \uc785\ub825", 20, color=WHITE, bullet=True)

# 7. 프롬프트
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "7. \ud504\ub86c\ud504\ud2b8 \ud3b8\uc9d1", 36, True, BLUE)
tf = add_text(slide, 1, 1.8, 11, 5, "", 20)
add_para(tf, "\uc5c5\uc885\ubcc4 AI \ud504\ub86c\ud504\ud2b8\ub97c \uc790\uc720\ub86d\uac8c \ucee4\uc2a4\ud140", 22, color=WHITE)
add_para(tf, "", 10)
add_para(tf, "\uc5c5\uc885 \ucd94\uac00/\uc0ad\uc81c \uac00\ub2a5", 20, color=WHITE, bullet=True)
add_para(tf, "AI \uc790\ub3d9 \uc0dd\uc131: \uc5c5\uc885 \ud398\ub974\uc18c\ub098\uc5d0 \ub9de\ub294 \ud504\ub86c\ud504\ud2b8 \uc790\ub3d9 \uc791\uc131", 20, color=WHITE, bullet=True)
add_para(tf, "\ube14\ub85c\uadf8 \ubcf8\ubb38 / \uc81c\ubaa9 \ud504\ub86c\ud504\ud2b8 \ubd84\ub9ac", 20, color=WHITE, bullet=True)
add_para(tf, "\uc81c\ubaa9 \ud0a4\uc6cc\ub4dc \ud615\uc2dd: XX\ub3d9 / XX\uc5ed / XX\uad6c \uc120\ud0dd", 20, color=WHITE, bullet=True)
add_para(tf, "Pixabay \uac80\uc0c9\uc5b4 1/2/3 \uc2ac\ub86f (\ud55c\uae00 \uc790\ub3d9 \ubc88\uc5ed)", 20, color=WHITE, bullet=True)

# 8. 설정
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "8. \uc124\uc815", 36, True, BLUE)
add_text(slide, 0.8, 1.5, 4, 0.6, "AI \uc124\uc815", 24, True, GREEN)
tf = add_text(slide, 1, 2.3, 5, 2, "", 20)
add_para(tf, "AI \uc81c\uacf5\uc790: GPT / Gemini", 20, color=WHITE, bullet=True)
add_para(tf, "API \ud0a4 \ucd5c\ub300 3\uac1c \ub4f1\ub85d", 20, color=WHITE, bullet=True)

add_text(slide, 0.8, 4, 4, 0.6, "\ub124\uc774\ubc84 \uacc4\uc815", 24, True, GREEN)
tf2 = add_text(slide, 1, 4.8, 5, 2, "", 20)
add_para(tf2, "\uacc4\uc815 1~9\ubc88 \ub4f1\ub85d \uac00\ub2a5", 20, color=WHITE, bullet=True)
add_para(tf2, "\ube14\ub85c\uadf8 ID / \ub124\uc774\ubc84 ID / PW / \uce74\ud14c\uace0\ub9ac", 20, color=WHITE, bullet=True)
add_para(tf2, "\uacc4\uc815\ubcc4 \ub370\uc774\ud130 \uc644\uc804 \ubd84\ub9ac", 20, color=WHITE, bullet=True)

add_text(slide, 7, 1.5, 4, 0.6, "Pixabay", 24, True, GREEN)
tf3 = add_text(slide, 7.2, 2.3, 5, 2, "", 20)
add_para(tf3, "API \ud0a4 \ub4f1\ub85d (\uc774\ubbf8\uc9c0 \uac80\uc0c9\uc6a9)", 20, color=WHITE, bullet=True)

# 9. 단축키
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "9. \ub2e8\ucd95\ud0a4", 36, True, BLUE)
for i, (k, d) in enumerate([("F5", "\ud06c\ub864\ub9c1 \uc2dc\uc791"), ("F6", "\uc911\ub2e8"),
                              ("F7", "\ud3ec\uc2a4\ud2b8 \uc0dd\uc131"), ("F8", "\ud3ec\uc2a4\ud2b8 \ubcf4\uae30 \ubc0f \ud3ec\uc2a4\ud305")]):
    y = 2 + i * 1.2
    add_text(slide, 2, y, 2, 0.8, k, 36, True, BLUE, PP_ALIGN.CENTER)
    add_text(slide, 4.5, y + 0.1, 6, 0.6, d, 24, False, WHITE)

# 10. 주의
slide = prs.slides.add_slide(prs.slide_layouts[6]); set_bg(slide)
add_text(slide, 0.8, 0.4, 8, 0.8, "10. \uc8fc\uc758\uc0ac\ud56d", 36, True, RED)
tf = add_text(slide, 1, 1.8, 11, 5, "", 20)
add_para(tf, "Chrome \ube0c\ub77c\uc6b0\uc800 \ud544\uc218 \uc124\uce58", 20, color=WHITE, bullet=True)
add_para(tf, "\ubcf4\uc548\ubb38\uc790(\uce90\ucc28) \ubc1c\uc0dd \uc2dc \uc218\ub3d9 \ud574\uacb0", 20, color=WHITE, bullet=True)
add_para(tf, "Chrome \uc5c5\ub370\uc774\ud2b8 \uc2dc \ud638\ud658 \ubb38\uc81c \ubc1c\uc0dd \uac00\ub2a5", 20, color=WHITE, bullet=True)
add_para(tf, "API \ud0a4 \uc678\ubd80 \ub178\ucd9c \uae08\uc9c0", 20, color=WHITE, bullet=True)
add_para(tf, "\ud3ec\uc2a4\ud305 \uac04\uaca9\uc744 \ub108\ubb34 \uc9e7\uac8c \ud558\uba74 \ub124\uc774\ubc84 \uc81c\uc7ac \uac00\ub2a5", 20, color=WHITE, bullet=True)

out = "C:/Users/kidth/OneDrive/Desktop/BlogMaster_사용설명서.pptx"
prs.save(out)
print(f"완료: {out} ({os.path.getsize(out)//1024}KB)")
