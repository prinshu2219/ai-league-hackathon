import unittest

from osft_lab.lora_utils import recommended_lora_settings, trainable_parameter_summary


class _FakeParam:
    def __init__(self, count, requires_grad):
        self._count = count
        self.requires_grad = requires_grad

    def numel(self):
        return self._count


class _FakeModel:
    def named_parameters(self):
        return [
            ("base.embeddings.weight", _FakeParam(1000, False)),
            ("base.transformer.layer.0.q_lin.lora_A", _FakeParam(80, True)),
            ("base.transformer.layer.0.v_lin.lora_B", _FakeParam(80, True)),
            ("classifier.weight", _FakeParam(60, True)),
        ]


class LoraUtilsTests(unittest.TestCase):
    def test_trainable_parameter_summary_counts_frozen_and_trainable_params(self):
        summary = trainable_parameter_summary(_FakeModel())

        self.assertEqual(
            summary,
            {
                "total_params": 1220,
                "trainable_params": 220,
                "frozen_params": 1000,
                "trainable_percent": 18.0328,
            },
        )

    def test_recommended_lora_settings_for_distilbert_target_attention_projections(self):
        settings = recommended_lora_settings(base_model_name="distilbert-base-uncased")

        self.assertEqual(settings["r"], 8)
        self.assertEqual(settings["lora_alpha"], 16)
        self.assertEqual(settings["lora_dropout"], 0.05)
        self.assertEqual(settings["target_modules"], ["q_lin", "v_lin"])


if __name__ == "__main__":
    unittest.main()
