# -*- coding: utf-8 -*-
"""나노바나나(Gemini 2.5 Flash Image)로 이사 이미지 생성 테스트"""
import json, os
from google import genai

c = json.load(open('config.json', encoding='utf-8'))
admin = c['api_keys_by_user']['admin']
gem = [k for k in admin.get('gemini_key_list', []) if k]
key = gem[0] if gem else c.get('ai_api_key','')
print("키 prefix:", key[:8])

client = genai.Client(api_key=key)

OUT = r"C:\Mac\Home\Desktop\나노테스트"
os.makedirs(OUT, exist_ok=True)

prompts = {
    "이사1": "한국의 이삿짐센터 직원들이 사다리차를 이용해 아파트에서 이삿짐을 옮기는 실사 사진, 자연광, 사실적인 다큐멘터리 스타일",
    "이사2": "한국 이사 트럭 앞에서 작업복 입은 기사님들이 갈색 종이박스를 나르는 실사 사진, 밝은 낮, 사실적",
    "이사3": "이삿짐 포장이사 - 거실에서 직원이 가구를 에어캡으로 포장하는 실사 사진, 사실적인 생활 사진",
    "요양원1": "한국 요양원에서 간호사가 할머니를 휠체어로 돌보며 미소 짓는 따뜻한 실사 사진, 밝은 실내",
}

models_to_try = ["gemini-2.5-flash-image", "gemini-2.5-flash-image-preview"]
model = None
for m in models_to_try:
    try:
        r = client.models.generate_content(model=m, contents="test simple red apple photo")
        model = m
        print("사용 모델:", m)
        break
    except Exception as e:
        print(f"  {m} 실패: {str(e)[:120]}")
if not model:
    print("이미지 생성 모델 사용 불가")
    raise SystemExit

for name, p in prompts.items():
    try:
        resp = client.models.generate_content(model=model, contents=p)
        saved = False
        for part in resp.candidates[0].content.parts:
            inline = getattr(part, "inline_data", None)
            if inline and getattr(inline, "data", None):
                with open(os.path.join(OUT, f"{name}.png"), "wb") as f:
                    f.write(inline.data)
                saved = True
                print(f"[{name}] 저장 완료")
        if not saved:
            print(f"[{name}] 이미지 파트 없음")
    except Exception as e:
        print(f"[{name}] 생성 실패: {str(e)[:150]}")

print("=== 완료:", OUT)
