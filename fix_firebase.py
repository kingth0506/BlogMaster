"""Firebase에서 expires_2="" 또는 expires_3="" 인 필드를 직접 삭제"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from users import _init_firebase
from firebase_admin import firestore

db = _init_firebase()
docs = list(db.collection('users').stream())
print(f"총 유저 수: {len(docs)}")

fixed = 0
for doc in docs:
    data = doc.to_dict()
    update = {}
    if data.get('expires_2') == '':
        update['expires_2'] = firestore.DELETE_FIELD
    if data.get('expires_3') == '':
        update['expires_3'] = firestore.DELETE_FIELD
    if update:
        doc.reference.update(update)
        fields = list(update.keys())
        print(f"수정: {doc.id} → {fields} 삭제")
        fixed += 1

print(f"\n완료: {fixed}명 수정")
