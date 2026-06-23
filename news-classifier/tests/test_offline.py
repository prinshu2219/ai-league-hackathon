#!/usr/bin/env python3
"""Offline tests — no API keys required."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ["APP_ENV"] = "test"
os.environ["OPENAI_API_KEY"] = "sk-test"
os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
os.environ["USE_DOMAIN_ROUTER"] = "true"


class TestDomainRouter(unittest.TestCase):
    def test_sports_headline(self):
        from app.llm.domain_classifier import classify_with_domain_router
        result = classify_with_domain_router(
            "India wins cricket series",
            "The team scored 350 runs in the final test match.",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.category, "sports")
        self.assertEqual(result.method, "domain_model")

    def test_tech_headline(self):
        from app.llm.domain_classifier import classify_with_domain_router
        result = classify_with_domain_router(
            "OpenAI launches new AI model",
            "The software startup released a new chip for machine learning.",
        )
        self.assertIsNotNone(result)
        self.assertEqual(result.category, "tech")

    def test_ambiguous_returns_none(self):
        from app.llm.domain_classifier import classify_with_domain_router
        result = classify_with_domain_router("Hello world", "Nothing specific here.")
        self.assertIsNone(result)


class TestTextUtils(unittest.TestCase):
    def test_strip_html(self):
        from app.text_utils import strip_html
        self.assertEqual(strip_html("<p>Hello <b>world</b></p>"), "Hello world")

    def test_compact_short(self):
        from app.text_utils import compact_article
        text, compacted = compact_article("Title", "Short body.", max_chars=1000)
        self.assertFalse(compacted)

    def test_compact_long(self):
        from app.text_utils import compact_article
        long_body = "word " * 5000
        text, compacted = compact_article("Title", long_body, max_chars=500)
        self.assertTrue(compacted)
        self.assertLess(len(text), 600)

    def test_chunks(self):
        from app.text_utils import split_into_chunks
        body = "a" * 7000
        chunks = split_into_chunks(body, chunk_size=3000)
        self.assertEqual(len(chunks), 3)


class TestRateLimiter(unittest.TestCase):
    def test_free_tier_limit(self):
        from app.rate_limiter import RateLimiter
        limiter = RateLimiter()
        for i in range(10):
            allowed, _ = limiter.check("user1", "free")
            self.assertTrue(allowed, f"Request {i+1} should be allowed")
        allowed, remaining = limiter.check("user1", "free")
        self.assertFalse(allowed)
        self.assertEqual(remaining, 0)

    def test_paid_tier_higher(self):
        from app.rate_limiter import RateLimiter
        limiter = RateLimiter()
        for i in range(50):
            allowed, _ = limiter.check("user2", "paid")
            self.assertTrue(allowed)


class TestCircuitBreaker(unittest.TestCase):
    def test_opens_after_failures(self):
        from app.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker()
        for _ in range(5):
            cb.record_failure()
        self.assertTrue(cb.is_open())

    def test_resets_on_success(self):
        from app.circuit_breaker import CircuitBreaker
        cb = CircuitBreaker()
        cb.record_failure()
        cb.record_success()
        self.assertFalse(cb.is_open())


class TestConfig(unittest.TestCase):
    def test_validate_missing_key(self):
        from app.config import Config
        original = Config.OPENAI_API_KEY
        Config.OPENAI_API_KEY = ""
        missing = Config.validate()
        self.assertIn("OPENAI_API_KEY", missing)
        Config.OPENAI_API_KEY = original


class TestLangChainChainStructure(unittest.TestCase):
    def test_chain_builds(self):
        from app.llm.chain import build_chain, prompt, parser
        chain = build_chain()
        self.assertIsNotNone(chain)
        self.assertIn("headline", prompt.input_variables)
        self.assertIn("body", prompt.input_variables)
        instructions = parser.get_format_instructions()
        self.assertIn("category", instructions)


if __name__ == "__main__":
    print("Running offline tests (no API keys needed)...\n")
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    print(f"\n{'✅ ALL PASSED' if result.wasSuccessful() else '❌ SOME FAILED'}")
    sys.exit(0 if result.wasSuccessful() else 1)
