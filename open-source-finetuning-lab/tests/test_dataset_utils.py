import unittest

from osft_lab.dataset_utils import build_label_maps, tokenize_batch


class _FakeTokenizer:
    def __init__(self):
        self.last_call = None

    def __call__(self, texts, truncation, padding, max_length):
        self.last_call = {
            "texts": texts,
            "truncation": truncation,
            "padding": padding,
            "max_length": max_length,
        }
        return {
            "input_ids": [[101, index + 1, 102] for index, _ in enumerate(texts)],
            "attention_mask": [[1, 1, 1] for _ in texts],
        }


class DatasetUtilsTests(unittest.TestCase):
    def test_build_label_maps_preserves_order(self):
        label2id, id2label = build_label_maps(["sadness", "joy", "love"])

        self.assertEqual(label2id, {"sadness": 0, "joy": 1, "love": 2})
        self.assertEqual(id2label, {0: "sadness", 1: "joy", 2: "love"})

    def test_tokenize_batch_adds_labels_and_uses_max_length(self):
        tokenizer = _FakeTokenizer()
        examples = {"text": ["I am happy", "I am worried"], "label": [1, 4]}

        tokenized = tokenize_batch(
            examples,
            tokenizer=tokenizer,
            text_column="text",
            label_column="label",
            max_length=32,
        )

        self.assertEqual(tokenized["input_ids"], [[101, 1, 102], [101, 2, 102]])
        self.assertEqual(tokenized["attention_mask"], [[1, 1, 1], [1, 1, 1]])
        self.assertEqual(tokenized["labels"], [1, 4])
        self.assertEqual(
            tokenizer.last_call,
            {
                "texts": ["I am happy", "I am worried"],
                "truncation": True,
                "padding": "max_length",
                "max_length": 32,
            },
        )


if __name__ == "__main__":
    unittest.main()
