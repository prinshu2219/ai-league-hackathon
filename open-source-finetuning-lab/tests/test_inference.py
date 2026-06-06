import unittest

from osft_lab.inference import format_probabilities, softmax, top_prediction


class InferenceTests(unittest.TestCase):
    def test_softmax_returns_probabilities_that_sum_to_one(self):
        probs = softmax([1.0, 2.0, 3.0])

        self.assertEqual(round(sum(probs), 6), 1.0)
        self.assertGreater(probs[2], probs[1])
        self.assertGreater(probs[1], probs[0])

    def test_top_prediction_maps_logits_to_label(self):
        prediction = top_prediction(
            [0.2, 2.3, -0.8],
            {0: "sadness", 1: "joy", 2: "anger"},
        )

        self.assertEqual(
            prediction,
            {"label": "joy", "score": softmax([0.2, 2.3, -0.8])[1]},
        )

    def test_format_probabilities_sorts_by_score_descending(self):
        formatted = format_probabilities(
            [0.1, 0.7, 0.2],
            {0: "sadness", 1: "joy", 2: "anger"},
        )

        self.assertEqual(
            formatted,
            [
                {"label": "joy", "score": 0.7},
                {"label": "anger", "score": 0.2},
                {"label": "sadness", "score": 0.1},
            ],
        )


if __name__ == "__main__":
    unittest.main()
