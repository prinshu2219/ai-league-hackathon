---
language: en
license: apache-2.0
library_name: peft
base_model: distilbert-base-uncased
datasets:
  - dair-ai/emotion
tags:
  - text-classification
  - lora
  - peft
  - pytorch
  - interview-prep
---

# Emotion LoRA DistilBERT

## Model Summary

This is a PEFT LoRA adapter for `distilbert-base-uncased` fine-tuned on `dair-ai/emotion` for six-way emotion classification: sadness, joy, love, anger, fear, and surprise.

The project is designed for L1 interview preparation. It demonstrates Hugging Face Hub usage, Datasets, Transformers, PyTorch device management, supervised fine-tuning, LoRA adapter training, evaluation, and model-card documentation.

## Intended Use

- Educational demonstration of basic supervised fine-tuning.
- Local emotion classification demo through Streamlit.
- Interview artifact for explaining open-source model workflows.

## Out-of-Scope Use

- Clinical or mental-health diagnosis.
- High-stakes sentiment or employee monitoring decisions.
- Production moderation without deeper evaluation and bias analysis.

## Training Data

Dataset: `dair-ai/emotion`

The dataset contains short English text samples labeled with one of six emotion classes. The project uses the standard train/validation/test splits exposed by Hugging Face Datasets.

## Training Procedure

- Base model: `distilbert-base-uncased`
- Adapter method: LoRA through PEFT
- Task type: sequence classification
- Target modules for DistilBERT: `q_lin`, `v_lin`
- Rank: `8`
- Alpha: `16`
- Dropout: `0.05`
- Default epochs: `3`
- Default batch size: `8`
- Optimizer: Trainer default AdamW
- Device order: CUDA, Apple MPS, CPU

## Evaluation

Run:

```bash
python3 scripts/evaluate.py --model-dir outputs/emotion-lora
```

The script writes:

- `reports/eval_metrics.json`
- `reports/confusion_matrix.png`

Metrics should be reported from the actual local run rather than copied into this card before training.

## Limitations

- DistilBERT is a compact encoder model, not a generative LLM.
- The task is classification, so it demonstrates supervised fine-tuning fundamentals without long-form generation.
- Labels are simplified emotion classes and may not capture mixed or subtle emotional states.
- Training quality depends on local hardware, selected sample limits, and random seed.

## Ethical Considerations

Emotion labels can be culturally and contextually ambiguous. This model should not be used to make high-stakes claims about a person. For production, add dataset review, subgroup analysis, calibration, monitoring, user consent controls, and a clear appeal path.
