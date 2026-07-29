# -*- coding: utf-8 -*-
import sys, os, time
sys.stdout.reconfigure(encoding="utf-8")
from naver_poster import NaverBlogPoster
p = NaverBlogPoster("x","x","todayisgood77", headless=False)
p.start_browser()
p.driver.get("https://blog.naver.com/PostView.naver?blogId=todayisgood77&logNo=224349466892")
time.sleep(3)
try:
    p.driver.set_window_position(60, 60); p.driver.set_window_size(1200, 950)
except Exception: pass
print(">>> 테스트글 열림:", p.driver.current_url)
print(">>> 30분 열어둡니다.")
time.sleep(1800)
