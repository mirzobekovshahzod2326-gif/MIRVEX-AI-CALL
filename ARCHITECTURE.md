# MIRVEX AI CALL — Texnik arxitektura va MVP rejasi (v0.1)

## 1. Asosiy cheklov
Oddiy Android ilovasi uyali qo'ng'iroq audiosiga ovoz qo'sha olmaydi. Shuning uchun AI
telefoniya qatlamida (SIP/VoIP), serverda ishlaydi. Ilova — boshqaruv va ko'rsatish paneli.

```
Qo'ng'iroqchi → Operator → (shartli yo'naltirish) → SIP/VoIP provayder
  → MIRVEX Server [Telephony adapter → Script engine ⇄ STT/TTS adapterlar]
  → PostgreSQL (sozlamalar, qisqa muddatli transkript)
  → WebSocket + FCM → Android ilova (Compose)
Ilova "Qo'shilish" → WebRTC/VoIP leg → konferensiya (AI jim)
```

## 2. Modullar (har biri almashtiriladigan interfeys)
| Modul | MVP tanlovi | Muqobil | Narx |
|---|---|---|---|
| Telephony | Twilio yoki Telnyx | Asterisk/FreeSWITCH + SIP trunk | Pullik (daqiqa + raqam) |
| STT | Whisper (open-source, o'z serveringizda) | Google/Azure STT | Bepul (GPU/CPU xarajati) / pullik |
| TTS | Google/Azure (uz, ru) | MMS-TTS tgk (tojik, bepul) | Pullik / bepul |
| Script engine | `core/script_engine.py` (tayyor) | — | Bepul |
| LLM (faqat ism/sabab ajratish, xulosa) | 2-bosqichdan keyin | Qoidalar asosida | Pullik |
| Backend | FastAPI + WebSocket | — | Bepul |
| DB | PostgreSQL | SQLite (dev) | Bepul |
| Push | FCM | — | Bepul |

Kalitlar faqat muhit o'zgaruvchilarida (`.env`, repoga kiritilmaydi).

## 3. MVP (eng zarur)
1. Bitta mamlakat, bitta operator, tillar: uz, ru, tg.
2. Skript: salom → AI ekanligi → ism → sabab → xayrlashuv.
3. Matn muharriri, ovoz/tezlik, jonli transkript, xulosa push.
4. "Qo'shilish" — 2-versiyaga (WebRTC murakkab).
5. Hozircha yo'q: 15 til, obuna, Business tarif.

## 4. Til holati (halol jadval)
Har til uchun STT, TTS va suhbat sifati real audioda tekshirilmaguncha "ishlaydi" deyilmaydi.
Hozir kod matnlari faqat uz/ru/tg uchun yozilgan va **ona tili egasi tekshiruvidan o'tmagan**.

## 5. Tekshirilmagan (real sinov kerak)
- Operator shartli yo'naltirishi va narxi (har mamlakatda alohida).
- Caller ID yo'naltirishda saqlanishi (Diversion/P-Asserted-Identity sarlavhalari).
- Uzbekiston/Tojikiston raqamlari yoki xalqaro SIP mavjudligi.
- Tojik STT/TTS sifati.
- Qonuniy talablar (shaxsiy ma'lumotlar, AI oshkor qilish) har mamlakat uchun.

## 6. Maxfiylik (dizayn qoidalari, kodda majburiy)
- Audio yozilmaydi; faqat matn. Avto-o'chirish muddati, "hammasini o'chirish".
- AI oshkor qilish matni (`DISCLOSURE`) egasi tomonidan o'chirib bo'lmaydi.
- Qo'ng'iroqchi rad etsa, qo'ng'iroq tugaydi.

## 7. Papka tuzilmasi
```
mirvex/
  core/script_engine.py      # 1-bosqich (tayyor, test qilingan)
  tests/
  docs/ARCHITECTURE.md
  server/   (2-bosqich: FastAPI, adapterlar, DB)
  android/  (3-bosqich: Compose)
```

## 8. Bosqichlar
- **1 (bajarildi):** script engine + 7 ta test.
- **2:** FastAPI, `/settings`, `/ws/transcript`, TTS/STT interfeyslari (mock + haqiqiy adapter), PostgreSQL.
- **3:** Twilio/Telnyx ulanishi, haqiqiy qo'ng'iroq sinovi bitta operator bilan.
- **4:** Android: sozlamalar, jonli transkript, FCM.
- **5:** Join Call, kontaktlar sinxronlash, 2-3-tillar sifat sinovi.

## 9. Ishga tushirish (1-bosqich)
```
python3 -m unittest discover -v     # Python 3.10+, qo'shimcha paket kerak emas
```
