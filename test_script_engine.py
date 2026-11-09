import unittest
from core.script_engine import *


def mk(**kw):
    return CallSession(Settings(owner_name="Aziz", **kw), "+998901234567")


class EngineTests(unittest.TestCase):
    def test_exact_owner_text_and_disclosure(self):
        s = mk(texts={"uz": {"greeting": "Salom, bu mening shaxsiy matnim."}})
        out = s.start()
        self.assertTrue(out[0].text.startswith("Salom, bu mening shaxsiy matnim."))
        self.assertIn("sun'iy intellekt", out[0].text)
        self.assertIn("ovoz yozib olinmaydi", out[0].text)

    def test_full_flow(self):
        s = mk(lang="ru"); s.start()
        s.on_caller_utterance("Иван")
        out = s.on_caller_utterance("Доставка")
        self.assertIsInstance(out[-1], Hangup)
        r = s.summary()
        self.assertEqual((r["caller_name"], r["reason"], r["state"]), ("Иван", "Доставка", "done"))

    def test_decline_ends_call(self):
        s = mk(lang="tg"); s.start()
        self.assertEqual(s.on_caller_utterance("Не")[0].reason, "caller_declined")

    def test_silence_then_hangup(self):
        s = mk(); s.start()
        self.assertEqual(s.on_silence()[0].text, DEFAULTS["uz"]["reprompt"])
        self.assertIsInstance(s.on_silence()[-1], Hangup)

    def test_owner_join_stops_ai(self):
        s = mk(); s.start(); s.on_caller_utterance("Ali")
        self.assertIsInstance(s.owner_join()[-1], OwnerJoin)
        self.assertEqual(s.on_caller_utterance("Salom"), [])

    def test_validation(self):
        for bad in (dict(lang="fr"), dict(speed=3), dict(texts={"uz": {"greeting": ""}}),
                    dict(texts={"uz": {"disclosure": "x"}})):
            with self.assertRaises(ValueError):
                mk(**bad)

    def test_all_languages_complete(self):
        for lang in SUPPORTED_LANGS:
            for key in EDITABLE:
                self.assertTrue(DEFAULTS[lang][key])
            self.assertTrue(DISCLOSURE[lang])
            self.assertTrue(mk(lang=lang).start())


if __name__ == "__main__":
    unittest.main()
