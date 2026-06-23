# IMDb BERT Fine-Tuning Project

An interview-ready open-source LLM/fine-tuning project built around the IMDb Movie Reviews dataset. The project fine-tunes `bert-base-uncased` for binary sentiment classification and gives you a concrete story to explain Hugging Face, PyTorch training loops, supervised fine-tuning, LoRA, evaluation, and open-source versus proprietary model trade-offs.

## Project Story

Use this summary in interviews:

> I fine-tuned a pre-trained BERT model on the IMDb Movie Reviews dataset to classify movie reviews as positive or negative. I used Hugging Face Transformers and Datasets, tokenized reviews with the BERT tokenizer, trained with a manual PyTorch loop using AdamW, monitored validation loss and F1-score, and evaluated the final model with accuracy, precision, recall, F1, and a confusion matrix.

The IMDb dataset has 50,000 labeled movie reviews: 25,000 train reviews and 25,000 test reviews, balanced between positive and negative labels. This project creates a validation split from the training set so hyperparameter decisions do not leak into the test set.

## Tech Stack

| Layer | Tool |
|---|---|
| Base model | `bert-base-uncased` |
| Dataset | IMDb Movie Reviews |
| Model hub | Hugging Face Hub |
| Training | PyTorch |
| NLP library | Hugging Face Transformers |
| Dataset loading | Hugging Face Datasets |
| Metrics | In-project metric helpers |
| Demo UI | Streamlit |

## Quick Start

```bash
cd imdb-bert-finetuning
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run offline tests, which do not download BERT or IMDb:

```bash
python3 tests/test_offline.py
```

Run a laptop-friendly smoke training pass:

```bash
python3 scripts/train.py \
  --max-train-samples 2000 \
  --max-eval-samples 1000 \
  --epochs 1 \
  --batch-size 8
```

Run full training when you have enough time and compute:

```bash
python3 scripts/train.py --epochs 3 --batch-size 16 --learning-rate 2e-5
```

Evaluate a saved model:

```bash
python3 scripts/evaluate.py --model-dir artifacts/model
```

Predict one review:

```bash
python3 scripts/predict.py \
  --text "The performances were excellent and the ending stayed with me." \
  --model-dir artifacts/model
```

Start the local UI:

```bash
streamlit run app_ui.py
```

## Project Structure

```text
imdb-bert-finetuning/
├── app/
│   ├── config.py        # TrainingConfig defaults: BERT, IMDb, AdamW hyperparameters
│   ├── data.py          # IMDb loading, validation split, tokenization, DataLoader creation
│   ├── evaluation.py    # Accuracy, precision, recall, F1, confusion matrix, metrics JSON
│   ├── inference.py     # Saved model loading and sentiment prediction helpers
│   └── training.py      # Manual PyTorch training and evaluation loops
├── scripts/
│   ├── train.py         # Fine-tuning CLI
│   ├── evaluate.py      # Test-set evaluation CLI
│   └── predict.py       # Single-text inference CLI
├── app_ui.py            # Streamlit demo
├── tests/test_offline.py
├── requirements.txt
└── README.md
```

## Training Setup

Default configuration:

| Setting | Value | Why |
|---|---:|---|
| Model | `bert-base-uncased` | Strong open-source baseline for text classification |
| Optimizer | AdamW | Standard transformer optimizer with decoupled weight decay |
| Learning rate | `2e-5` | Stable BERT fine-tuning baseline |
| Batch size | `16` | Good balance between memory and gradient stability |
| Epochs | `3` | Enough to adapt BERT without excessive overfitting risk |
| Max length | `256` | Keeps long reviews manageable on laptop hardware |
| Metrics | Accuracy, precision, recall, F1 | Accuracy is useful because IMDb is balanced; F1 catches class-specific issues |

Expected result for a normal BERT IMDb run is usually around 92-95 percent accuracy depending on sequence length, batch size, hardware, seed, and whether you train on the full dataset. The smoke command is only for verifying the pipeline; it should not be presented as final benchmark performance.

## What Happens in `from_pretrained()`

When the code calls `AutoTokenizer.from_pretrained("bert-base-uncased")`, Hugging Face downloads tokenizer artifacts such as the vocabulary, tokenizer config, and special token mapping if they are not already cached locally.

When the code calls `AutoModelForSequenceClassification.from_pretrained(...)`, Hugging Face downloads the model config and pre-trained weights. The config defines the architecture: number of layers, hidden size, attention heads, dropout, and label mapping. The weights contain the language knowledge BERT learned during pre-training.

The tokenizer converts raw text into:

- `input_ids`: numeric token IDs from the WordPiece vocabulary
- `attention_mask`: 1 for real tokens, 0 for padding
- optional `token_type_ids`: segment IDs used by BERT-style models

The model converts token IDs into embeddings, processes them through transformer layers, and sends the pooled representation into a classification head that predicts negative or positive sentiment.

## PyTorch Training Loop

The important training loop steps are in `app/training.py`:

1. `model.train()` enables training behavior such as dropout.
2. Each batch provides `input_ids`, `attention_mask`, and `labels`.
3. `optimizer.zero_grad()` clears previous gradients.
4. `outputs = model(**batch)` runs the forward pass and computes cross-entropy loss.
5. `loss.backward()` calculates gradients with autograd.
6. `optimizer.step()` updates model parameters.
7. `scheduler.step()` adjusts the learning rate.
8. Metrics are tracked from logits and labels.
9. Validation uses `model.eval()` and `torch.no_grad()` to disable dropout and gradient storage.

If you forget `optimizer.zero_grad()`, PyTorch accumulates gradients by default. That means gradients from previous batches carry into the next update, producing larger-than-intended updates. Symptoms include unstable loss, large gradient norms, and poor convergence. Gradient accumulation is only desirable when done deliberately to simulate a larger effective batch size.

## Overfitting Explanation

Signs of overfitting:

- Training loss keeps decreasing while validation loss increases.
- Training accuracy improves while validation F1 plateaus or drops.
- Test metrics are much worse than validation metrics.

Mitigations used or discussed in this project:

- Use a small learning rate (`2e-5`) so BERT is adapted rather than overwritten.
- Limit training to a few epochs.
- Monitor validation metrics after every epoch.
- Use BERT's built-in dropout.
- Keep the IMDb test split untouched until final evaluation.

For severe overfitting, you can add early stopping, increase dropout, reduce model size, reduce epochs, increase weight decay, or collect more representative data.

## Full Fine-Tuning vs LoRA

This project performs full fine-tuning: all BERT parameters are trainable. This is practical for BERT-sized models and gives a clean interview story for supervised fine-tuning.

LoRA, or Low-Rank Adaptation, is parameter-efficient fine-tuning. The base model weights are frozen, and small trainable low-rank matrices are inserted into selected layers, often attention projections.

Instead of learning a full update matrix:

```text
Delta W with shape d x k
```

LoRA represents the update as:

```text
Delta W = B A
```

where:

```text
A has shape r x k
B has shape d x r
r is much smaller than d and k
```

A full 1024 x 1024 update has 1,048,576 parameters. With LoRA rank 8, the adapter has:

```text
1024 x 8 + 8 x 1024 = 16,384 parameters
```

Choose LoRA when working with larger LLMs, limited GPU memory, or many task-specific adapters. Choose full fine-tuning when the model is smaller, the task is narrow, and you can afford updating all weights.

## Open Source vs Proprietary Models

Choose an open-source model when:

- Data cannot leave your infrastructure.
- You need domain-specific customization.
- You want model weight control and reproducibility.
- High-volume traffic makes self-hosting cheaper over time.
- Latency is better with local or private-cloud deployment.

Choose a proprietary API when:

- You need strongest general reasoning immediately.
- You want minimal infrastructure and maintenance.
- Traffic is low or unpredictable.
- You do not have enough domain data to fine-tune.
- Vendor-hosted safety, scaling, and monitoring are acceptable.

Self-hosting costs include GPU or CPU compute, model storage, dataset storage, bandwidth, monitoring, deployment automation, scaling, security patching, and engineering maintenance. Open source gives control, but you own operations.

## Interview Q&A

### Tell me about your open-source model experience.

I fine-tuned `bert-base-uncased`, an open-source transformer model from Hugging Face, on the IMDb Movie Reviews dataset. I loaded the tokenizer and model with `from_pretrained()`, tokenized reviews into `input_ids` and `attention_mask`, trained using PyTorch and AdamW, and evaluated with accuracy, precision, recall, and F1. I also built a CLI and Streamlit demo to run inference from the saved model.

### Why did you choose BERT?

BERT is a strong, well-known open-source encoder model for text classification. Its bidirectional self-attention helps it understand context from both left and right sides of a token, which matters for sentiment where negation and contrast can change meaning.

### Did you train from scratch?

No. I used transfer learning. BERT already learned general language representations during pre-training, and I fine-tuned those weights on labeled IMDb reviews. This is faster and needs much less data than training a transformer from scratch.

### What optimizer and hyperparameters did you use?

I used AdamW with a learning rate of `2e-5`, batch size `16`, and `3` epochs. AdamW is commonly used for transformers because it applies weight decay correctly. The small learning rate avoids destroying useful pre-trained representations, and three epochs are usually enough for a balanced supervised dataset like IMDb.

### How did you evaluate the model?

I used a validation split during training and saved final test metrics separately. The project reports accuracy, precision, recall, F1, and confusion matrix values. Accuracy is meaningful because IMDb is balanced, but F1 is also useful because it combines precision and recall.

### What were the main challenges?

Long reviews can exceed the model input length, so I used truncation and padding with a fixed max sequence length. I also monitored validation loss because higher learning rates can make transformer fine-tuning unstable.

### How would you explain LoRA if asked?

LoRA freezes the base model and trains small low-rank adapter matrices instead of updating every weight. It reduces trainable parameters, optimizer state, memory use, and checkpoint size. I used full fine-tuning here because BERT is manageable, but I would consider LoRA for larger LLMs.

### What are the first three questions before choosing open source fine-tuning or a proprietary API?

First, what are the privacy and compliance constraints? Second, does the task need domain-specific customization or top-tier general reasoning? Third, what are the cost and operational constraints, including traffic volume, latency, infrastructure, and maintenance?

## File-to-Interview Topic Map

| Topic | File |
|---|---|
| Hugging Face tokenizer/model loading | `app/data.py`, `app/training.py`, `app/inference.py` |
| Tokenization, padding, truncation | `app/data.py` |
| PyTorch train/eval loop | `app/training.py` |
| AdamW, scheduler, epochs | `app/training.py`, `app/config.py` |
| Metrics and confusion matrix | `app/evaluation.py` |
| Saved-model inference | `app/inference.py`, `scripts/predict.py` |
| Demo UI | `app_ui.py` |
| Offline tests | `tests/test_offline.py` |

## Troubleshooting

If model download fails, check network access and Hugging Face availability. The first training run downloads the dataset and model into `hf_cache/`.

If training is slow, use:

```bash
python3 scripts/train.py --max-train-samples 1000 --max-eval-samples 500 --epochs 1 --batch-size 4
```

If you run out of memory, reduce `--batch-size` and `--max-length`. For Apple Silicon, the code will use MPS when PyTorch reports it as available. Use `--cpu-only` if you see MPS-specific runtime issues.

