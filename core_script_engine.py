"""MIRVEX call-script engine (Stage 1).

Deterministic state machine: the AI says EXACTLY the owner's text.
No telephony, STT or TTS here - those plug in via the Action objects.
Pure standard library, so it is easy to test and reuse on the server.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum

MAX_TEXT_LEN = 500
SUPPORTED_LANGS = ("uz", "ru", "tg")  # only languages with reviewed texts

# Mandatory transparency text. The owner CANNOT remove or edit it.
# NOTE: uz/ru/tg wording must be reviewed by native speakers before release.
DISCLOSURE = {
    "uz": "Men {owner}ning sun'iy intellekt yordamchisiman. Suhbat matn shaklida qayd etiladi, ovoz yozib olinmaydi.",
    "ru": "Я ИИ-ассистент {owner}. Разговор фиксируется в виде текста, аудио не записывается.",
    "tg": "Ман ёрдамчии зеҳни сунъии {owner} ҳастам. Сӯҳбат ҳамчун матн сабт мешавад, садо сабт намешавад.",
}
DEFAULTS = {
    "uz": {"greeting": "Assalomu alaykum.", "ask_name": "Iltimos, ismingizni ayting.",
           "ask_reason": "Qo'ng'iroq sababini qisqacha ayting.",
           "closing": "Rahmat. Ma'lumotingiz egasiga yetkaziladi. Xayr.",
           "handoff": "Iltimos, kuting, egasi ulanmoqda.",
           "reprompt": "Eshitmadim, takrorlay olasizmi?"},
    "ru": {"greeting": "Здравствуйте.", "ask_name": "Пожалуйста, назовите ваше имя.",
           "ask_reason": "Коротко скажите, по какому вопросу вы звоните.",
           "closing": "Спасибо. Ваше сообщение будет передано владельцу. До свидания.",
           "handoff": "Пожалуйста, подождите, владелец подключается.",
           "reprompt": "Я не расслышал, повторите, пожалуйста."},
    "tg": {"greeting": "Салом алейкум.", "ask_name": "Лутфан номатонро бигӯед.",
           "ask_reason": "Сабаби занг задаништонро кӯтоҳ бигӯед.",
           "closing": "Ташаккур. Маълумоти шумо ба соҳиб расонида мешавад. Хайр.",
           "handoff": "Лутфан интизор шавед, соҳиб пайваст мешавад.",
           "reprompt": "Нашунидам, лутфан такрор кунед."},
}
REFUSAL_WORDS = {
    "uz": {"yo'q", "yoq", "xohlamayman", "rozi emasman"},
    "ru": {"нет", "не надо", "не согласен", "не хочу"},
    "tg": {"не", "нест", "намехоҳам", "розӣ нестам"},
}
EDITABLE = ("greeting", "ask_name", "ask_reason", "closing", "handoff", "reprompt")


class State(Enum):
    NEW = "new"
    ASK_NAME = "ask_name"
    ASK_REASON = "ask_reason"
    DONE = "done"
    HANDOFF = "handoff"
    DECLINED = "declined"


@dataclass
class Say:
    text: str
    lang: str


@dataclass
class Hangup:
    reason: str


@dataclass
class OwnerJoin:
    pass


@dataclass
class Settings:
    owner_name: str
    lang: str = "uz"
    voice: str = "default"
    speed: float = 1.0  # 0.5 .. 2.0, passed to the TTS provider
    texts: dict = field(default_factory=dict)  # {lang: {key: custom text}}

    def validate(self) -> None:
        if self.lang not in SUPPORTED_LANGS:
            raise ValueError(f"unsupported language: {self.lang}")
        if not self.owner_name.strip():
            raise ValueError("owner_name is required")
        if not 0.5 <= self.speed <= 2.0:
            raise ValueError("speed must be between 0.5 and 2.0")
        for lang, items in self.texts.items():
            if lang not in SUPPORTED_LANGS:
                raise ValueError(f"unsupported language: {lang}")
            for key, value in items.items():
                if key not in EDITABLE:
                    raise ValueError(f"'{key}' is not editable")
                if not value.strip() or len(value) > MAX_TEXT_LEN:
                    raise ValueError(f"'{key}' must be 1-{MAX_TEXT_LEN} characters")

    def text(self, key: str, lang: str | None = None) -> str:
        lang = lang or self.lang
        return self.texts.get(lang, {}).get(key) or DEFAULTS[lang][key]


class CallSession:
    MAX_REPROMPTS = 1

    def __init__(self, settings: Settings, caller_number: str = ""):
        settings.validate()
        self.s = settings
        self.caller_number = caller_number
        self.state = State.NEW
        self.caller_name = ""
        self.reason = ""
        self.transcript: list[tuple[float, str, str]] = []  # (ts, speaker, text)
        self._silences = 0

    def _say(self, text: str) -> Say:
        self.transcript.append((time.time(), "ai", text))
        return Say(text, self.s.lang)

    def start(self) -> list:
        """Call answered. Disclosure is ALWAYS spoken, after the owner's greeting."""
        disclosure = DISCLOSURE[self.s.lang].format(owner=self.s.owner_name.strip())
        self.state = State.ASK_NAME
        return [self._say(f"{self.s.text('greeting')} {disclosure}"),
                self._say(self.s.text("ask_name"))]

    def on_caller_utterance(self, text: str) -> list:
        text = text.strip()
        if self.state in (State.DONE, State.HANDOFF, State.DECLINED, State.NEW) or not text:
            return []
        self.transcript.append((time.time(), "caller", text))
        self._silences = 0
        if text.lower().strip(" .!") in REFUSAL_WORDS[self.s.lang] and self.state == State.ASK_NAME:
            self.state = State.DECLINED
            return [Hangup("caller_declined")]
        if self.state == State.ASK_NAME:
            self.caller_name = text
            self.state = State.ASK_REASON
            return [self._say(self.s.text("ask_reason"))]
        self.reason = text  # ASK_REASON
        self.state = State.DONE
        return [self._say(self.s.text("closing")), Hangup("completed")]

    def on_silence(self) -> list:
        if self.state not in (State.ASK_NAME, State.ASK_REASON):
            return []
        self._silences += 1
        if self._silences > self.MAX_REPROMPTS:
            self.state = State.DONE
            return [self._say(self.s.text("closing")), Hangup("no_response")]
        return [self._say(self.s.text("reprompt"))]

    def owner_join(self) -> list:
        """Owner taps 'Join': AI stops, call control goes to the owner."""
        if self.state in (State.DONE, State.DECLINED):
            return []
        self.state = State.HANDOFF
        return [self._say(self.s.text("handoff")), OwnerJoin()]

    def summary(self) -> dict:
        return {"caller_number": self.caller_number, "caller_name": self.caller_name,
                "reason": self.reason, "lang": self.s.lang, "state": self.state.value,
                "transcript": [{"ts": t, "speaker": sp, "text": tx} for t, sp, tx in self.transcript]}
