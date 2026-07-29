# -*- coding: utf-8 -*-
"""블로그 댓글 자동답글용 문구 풀 생성 — 자연스럽고 다양하게 ~2000개 (봇 느낌 최소화)"""
import json, itertools, random

TARGET = 2000

# 다양한 조각들 (구조가 한 가지로 안 보이게 패턴 여러 개 + 어휘 다양)
thanks = [
    "댓글 감사합니다", "댓글 남겨주셔서 감사해요", "방문 감사합니다", "들러주셔서 감사해요",
    "와주셔서 감사합니다", "읽어주셔서 감사해요", "관심 가져주셔서 감사합니다", "공감 감사해요",
    "따뜻한 댓글 감사합니다", "댓글 보고 힘이 나네요", "댓글 너무 반가워요", "이렇게 댓글까지 감사해요",
    "소중한 댓글 감사합니다", "정성스런 댓글 감사해요", "댓글로 인사 주셔서 감사해요",
    "바쁘실 텐데 들러주셔서 감사해요", "좋은 말씀 감사합니다", "응원 댓글 감사해요",
    "잊지 않고 와주셔서 감사해요", "챙겨주셔서 감사합니다", "댓글 하나하나 감사해요",
    "관심과 댓글 감사드려요", "먼저 인사 주셔서 감사해요", "다녀가주셔서 감사합니다",
]
react = [
    "좋게 봐주셔서 기뻐요", "도움이 되셨다니 다행이에요", "공감해주시니 뿌듯하네요",
    "그렇게 말씀해주시니 감사하죠", "저도 같은 생각이에요", "맞아요 정말 그렇더라고요",
    "좋게 읽어주셔서 감사해요", "이런 반응 너무 감사해요", "도움 되셨으면 좋겠어요",
    "재밌게 보셨다니 기뻐요", "유익하셨다니 다행입니다", "공감되셨다니 감사해요",
    "관심 가져주시니 힘이 나요", "저도 덕분에 배워가요", "말씀 너무 감사하죠",
    "따뜻하게 봐주셔서 감동이에요", "이렇게 공감받으니 뿌듯해요", "정말 반가운 말씀이에요",
    "좋은 하루의 시작 같아요", "그리 말씀해주시니 감사할 따름이에요",
]
ask_again = [
    "자주 들러주세요", "또 놀러오세요", "다음에 또 봬요", "종종 소통해요",
    "앞으로도 자주 와주세요", "편하게 소통해요", "다음 글도 기대해주세요",
    "또 좋은 글로 찾아올게요", "이웃추가하고 자주 봬요", "댓글로 또 만나요",
    "자주 소통하면 좋겠어요", "언제든 편하게 들러주세요", "다음에도 놀러와주세요",
    "이웃으로 오래 봬요", "종종 안부 나눠요", "다음 이야기도 들려드릴게요",
    "앞으로도 잘 부탁드려요", "서로 자주 오가요",
]
wish = [
    "좋은 하루 보내세요", "행복한 하루 되세요", "오늘도 좋은 하루 되세요",
    "남은 하루도 화이팅이에요", "따뜻한 하루 보내세요", "편안한 저녁 되세요",
    "활기찬 하루 되세요", "기분 좋은 하루 되세요", "건강 잘 챙기세요", "늘 좋은 일만 가득하세요",
    "즐거운 하루 되세요", "포근한 하루 보내세요", "웃음 가득한 하루 되세요",
    "무탈한 하루 되세요", "산뜻한 하루 보내세요", "평안한 하루 되세요",
    "행복 가득한 날 되세요", "오늘도 힘내세요", "좋은 일만 생기길 바라요",
    "따뜻한 저녁 보내세요", "편안한 밤 되세요", "즐거운 한 주 되세요",
]
tails = ["", "", "", " ㅎㅎ", " ㅎㅎ", "~", "!", " :)", " ^^", " ☺", " 😊"]

out = set()

def add(s):
    s = s.strip()
    if 4 <= len(s) <= 40:
        out.add(s)

# 패턴 1: 감사 + 마무리
for t, w in itertools.product(thanks, wish):
    add(f"{t}! {w}{random.choice(tails)}")
# 패턴 2: 감사 + 다시방문
for t, a in itertools.product(thanks, ask_again):
    add(f"{t}~ {a}{random.choice(tails)}")
# 패턴 3: 반응 + 마무리
for r, w in itertools.product(react, wish):
    add(f"{r}. {w}{random.choice(tails)}")
# 패턴 4: 감사 + 반응
for t, r in itertools.product(thanks, react):
    add(f"{t}, {r}{random.choice(tails)}")
# 패턴 5: 반응 + 다시방문
for r, a in itertools.product(react, ask_again):
    add(f"{r}. {a}{random.choice(tails)}")
# 패턴 6: 감사 + 다시방문 (마무리 없이 짧게)
for t, a in itertools.product(thanks, ask_again):
    add(f"{t}~ {a}")
# 패턴 7: 단문(감사/마무리/다시방문/반응 단독)
for t in thanks:
    add(f"{t}{random.choice(tails)}")
for w in wish:
    add(f"{w}{random.choice(tails)}")
for a in ask_again:
    add(f"{a}{random.choice(tails)}")
for r in react:
    add(f"{r}{random.choice(tails)}")

phrases = list(out)
random.seed(7)
random.shuffle(phrases)          # 한 번 섞어서 비슷한 게 연달아 안 나오게
phrases = phrases[:TARGET]

json.dump(phrases, open("reply_phrases.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"생성 완료: {len(phrases)}개 -> reply_phrases.json")
print("예시 10개:")
for p in phrases[:10]:
    print("  -", p)
