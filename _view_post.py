# -*- coding: utf-8 -*-
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8")
from naver_poster import NaverBlogPoster
p = NaverBlogPoster("x","x","todayisgood77", headless=False)
p.start_browser()
# 공개글이라 로그인 없이 열림. 본문 iframe 직접 열기
p.driver.get("https://blog.naver.com/PostView.naver?blogId=todayisgood77&logNo=224349466892")
time.sleep(5)
print(">>> URL:", p.driver.current_url)
print(">>> 글 열림 (2분). 사진먼저 배치 확인.")
time.sleep(120)
