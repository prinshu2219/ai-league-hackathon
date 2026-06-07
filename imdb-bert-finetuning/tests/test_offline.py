import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class TestTrainingConfig(unittest.TestCase):
    def test_default_config_matches_interview_story(self):
        from app.config import TrainingConfig

        config = TrainingConfig()

        self.assertEqual(config.model_name, "bert-base-uncased")
        self.assertEqual(config.dataset_name, "imdb")
        self.assertEqual(config.learning_rate, 2e-5)
        self.assertEqual(config.batch_size, 16)
        self.assertEqual(config.epochs, 3)
        self.assertEqual(config.max_length, 256)

    def test_output_paths_are_relative_to_output_dir(self):
        from app.config import TrainingConfig

        config = TrainingConfig(output_dir="custom-artifacts")

        self.assertEqual(config.model_dir, Path("custom-artifacts/model"))
        self.assertEqual(config.metrics_path, Path("custom-artifacts/metrics.json"))
        self.assertEqual(config.history_path, Path("custom-artifacts/training_history.json"))


class TestMetrics(unittest.TestCase):
    def test_binary_metrics_for_known_predictions(self):
        from app.evaluation import compute_binary_metrics

        metrics = compute_binary_metrics(labels=[1, 0, 1, 0], predictions=[1, 0, 0, 0])

        self.assertEqual(metrics["accuracy"], 0.75)
        self.assertEqual(metrics["precision"], 1.0)
        self.assertEqual(metrics["recall"], 0.5)
        self.assertAlmostEqual(metrics["f1"], 0.6667, places=4)
        self.assertEqual(metrics["confusion_matrix"], {"tn": 2, "fp": 0, "fn": 1, "tp": 1})

    def test_metrics_handle_no_positive_predictions(self):
        from app.evaluation import compute_binary_metrics

        metrics = compute_binary_metrics(labels=[1, 0, 1, 0], predictions=[0, 0, 0, 0])

        self.assertEqual(metrics["precision"], 0.0)
        self.assertEqual(metrics["recall"], 0.0)
        self.assertEqual(metrics["f1"], 0.0)


class TestInferenceHelpers(unittest.TestCase):
    def test_label_mapping(self):
        from app.inference import label_from_id

        self.assertEqual(label_from_id(0), "negative")
        self.assertEqual(label_from_id(1), "positive")

        with self.assertRaises(ValueError):
            label_from_id(2)

    def test_prediction_format_from_logits(self):
        from app.inference import prediction_from_logits

        result = prediction_from_logits([-1.0, 2.0])

        self.assertEqual(result["label"], "positive")
        self.assertEqual(result["label_id"], 1)
        self.assertGreater(result["confidence"], 0.9)


class TestDeviceSelection(unittest.TestCase):
    def test_cpu_device_when_accelerators_disabled(self):
        from app.training import select_device

        device = select_device(prefer_mps=False, prefer_cuda=False)

        self.assertEqual(str(device), "cpu")


class TestArtifactWriting(unittest.TestCase):
    def test_save_metrics_writes_json(self):
        from app.evaluation import save_metrics

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "metrics.json"
            save_metrics({"accuracy": 0.75}, path)

            self.assertEqual(json.loads(path.read_text()), {"accuracy": 0.75})


if __name__ == "__main__":
    unittest.main(verbosity=2)
