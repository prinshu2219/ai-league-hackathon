# L1 Open Source LLM Ecosystems and Basic Fine-Tuning - Evaluation Prep Guide

## Purpose

Use this guide to prepare for a 15-minute L1 interview on open-source LLM ecosystems and basic fine-tuning. The goal is to explain concepts clearly and tie them to the Open Source Fine-Tuning Lab project.

## Assessment Gaps This Project Fixes

| Sub-topic | Prior gap | What to say now |
|---|---|---|
| Hugging Face Ecosystem | Too much focus on `from_pretrained`; missed Hub, Datasets, Spaces, model cards, versioning | This project uses Hub model IDs, `load_dataset`, Transformers, PEFT, an optional Hub upload script, model card, and a Streamlit app that can become a Space |
| PyTorch Basics | Did not explain tensors, device movement, train/inference loops | `scripts/pytorch_basics.py` demonstrates tensors, `.to(device)`, `model.train()`, `loss.backward()`, `optimizer.step()`, `model.eval()`, and `torch.no_grad()` |
| Basic Supervised Fine-Tuning | LoRA/QLoRA experience was good, but hyperparameter reasoning was vague | This guide explains rank, target layers, learning rate, early stopping, validation, metrics, and overfitting controls |
| Open-source vs Proprietary | Already strong | Keep using compliance and local-hosting examples, but add governance and maintenance trade-offs |

## Project in One Paragraph

I built Open Source Fine-Tuning Lab to practice the full Hugging Face and PyTorch workflow. It loads `dair-ai/emotion` using Hugging Face Datasets, tokenizes text with `AutoTokenizer`, loads `distilbert-base-uncased` using `AutoModelForSequenceClassification`, and applies PEFT LoRA adapters to the DistilBERT attention projection layers. Training uses Hugging Face `Trainer`, but the project also includes a separate PyTorch basics script that shows raw tensors, DataLoader, device placement, training loop, and inference loop. After training, the adapter is saved locally, evaluated on the test split, documented with a model card, and can optionally be uploaded to Hugging Face Hub or served through a Streamlit app.

## Criterion 1: Hugging Face Ecosystem

### Core Concepts

Hugging Face is more than the Transformers library. It is an ecosystem:

- **Hub:** hosts models, datasets, Spaces, model cards, files, commits, versions, and discussions.
- **Transformers:** provides model and tokenizer APIs like `AutoTokenizer.from_pretrained()` and `AutoModelForSequenceClassification.from_pretrained()`.
- **Datasets:** provides `load_dataset()`, dataset splits, mapping, filtering, and efficient preprocessing.
- **PEFT:** supports parameter-efficient fine-tuning methods like LoRA.
- **Spaces:** hosts demos using Streamlit, Gradio, or static apps.
- **Model cards:** document intended use, training data, metrics, limitations, and ethical considerations.

### How This Project Uses It

- Loads the base model from the Hub: `distilbert-base-uncased`.
- Loads the dataset from the Hub: `dair-ai/emotion`.
- Uses `AutoTokenizer` and `AutoModelForSequenceClassification` so the code is model-family aware.
- Saves a local PEFT adapter under `outputs/emotion-lora`.
- Includes `MODEL_CARD.md` for Hub-ready documentation.
- Includes `scripts/push_to_hub.py` to create/upload a Hub repository.
- Uses Streamlit in `app.py`, which is compatible with a future Hugging Face Space.

### Likely Questions

**Q: What is `from_pretrained()` doing?**

It resolves a model or tokenizer identifier from the Hub or a local directory, downloads the required config/files if needed, caches them, and instantiates the correct tokenizer or model class.

**Q: What are model cards?**

Model cards are documentation files, usually `README.md` on the Hub, that explain what the model is, how it was trained, what data and metrics were used, intended use, limitations, and ethical risks.

**Q: What is a Space?**

A Space is a hosted demo app on Hugging Face. For this project, `app.py` could be deployed as a Streamlit Space so interviewers or teammates can try the classifier in a browser.

**Q: How does versioning work on the Hub?**

Hub repositories are Git-backed. Model files, tokenizer files, adapter weights, and model cards are versioned through commits, so you can track exactly which artifacts were used.

## Criterion 2: PyTorch Basics for Inference and Training

### Core Concepts

- A tensor is the basic numeric data structure in PyTorch.
- Tensor shape tells you dimensions, such as `[batch_size, sequence_length]`.
- Tensor dtype controls numeric type, such as `float32` for features or `long` for class labels.
- Device placement matters: model and tensors must be on the same device.
- `model.train()` enables training behavior.
- `loss.backward()` computes gradients.
- `optimizer.step()` updates trainable parameters.
- `model.eval()` switches to inference behavior.
- `torch.no_grad()` disables gradient tracking during inference.

### How This Project Uses It

`scripts/pytorch_basics.py` shows the raw loop. The fine-tuning script uses `Trainer`, but the same concepts are still happening under the hood: batches move to device, logits are computed, loss is calculated, gradients are backpropagated, and optimizer steps update trainable LoRA parameters.

### Device Explanation

The project chooses devices in this order:

1. CUDA for NVIDIA GPU.
2. MPS for Apple Silicon GPU.
3. CPU fallback.

Interview line:

"I explicitly handle device placement. The helper checks CUDA first, then Apple MPS, then CPU. During training or inference, both the model and input tensors are moved to the selected device using `.to(device)`. If tensors and model are on different devices, PyTorch will throw a runtime error."

### Likely Questions

**Q: What happens in a PyTorch training loop?**

For each batch, move data to device, clear old gradients with `optimizer.zero_grad()`, run a forward pass, compute loss, call `loss.backward()` to compute gradients, and call `optimizer.step()` to update parameters.

**Q: Why use `torch.no_grad()` during inference?**

It avoids storing gradients and computation history. That reduces memory usage and makes inference faster.

**Q: Why call `model.eval()`?**

It switches layers like dropout and batch norm into evaluation behavior. Even if DistilBERT does not use batch norm, dropout behavior still matters.

## Criterion 3: Basic Supervised Fine-Tuning

### What Supervised Fine-Tuning Means

Supervised fine-tuning trains a model on labeled input-output examples. In this project, each input is a text sample and the output is one of six emotion labels.

### Pipeline

```text
Load dataset -> tokenize text -> load base model -> attach LoRA -> train -> validate -> save adapter -> evaluate -> demo
```

### LoRA Explanation

LoRA freezes the base model weights and trains small low-rank matrices inserted into selected layers. This reduces the number of trainable parameters, lowers compute needs, and makes the adapter easy to save and share.

### Why Rank 8

Rank controls adapter capacity. A higher rank gives more trainable capacity but uses more memory and can overfit small datasets. Rank 8 is a conservative starting point for an L1 demo because it is small, fast, and commonly sufficient for a narrow classification task. If validation accuracy plateaued too low, I would try ranks like 16 or target more layers. If overfitting appeared, I would reduce rank, add dropout, or stop earlier.

### Why Target `q_lin` and `v_lin`

DistilBERT attention layers have query and value projection modules named `q_lin` and `v_lin`. Adapting these projections lets LoRA influence attention behavior without training the full model.

### Hyperparameters to Explain

| Hyperparameter | Default | Reason |
|---|---:|---|
| Learning rate | `2e-4` | LoRA adapters can usually use a higher LR than full fine-tuning |
| Batch size | `8` | Safe for CPU/Mac demos |
| Epochs | `3` | Enough for a small supervised task without overcommitting |
| LoRA rank | `8` | Small adapter capacity for an L1 project |
| LoRA alpha | `16` | Scaling factor, commonly paired with rank 8 |
| LoRA dropout | `0.05` | Regularization to reduce overfitting |
| Weight decay | `0.01` | Helps regularize trainable weights |

### Evaluation

The project evaluates on the test split and writes:

- accuracy
- macro precision
- macro recall
- macro F1
- confusion matrix

Interview line:

"I do not judge fine-tuning only by training loss. I track validation accuracy during training and run a separate test evaluation afterward. The confusion matrix helps identify which emotion labels are confused with each other."

## Criterion 4: Open-Source vs Proprietary Trade-offs

### Strong Answer

"For sensitive or regulated data, open-source local hosting can be preferable because the data does not need to leave the organization. That mattered in HIPAA-style scenarios. But open-source is not automatically safer. You still need access controls, audit logs, encryption, data retention, evaluation, and monitoring. Proprietary APIs are faster to prototype and often stronger for broad reasoning, but they introduce vendor dependency, per-token costs, and data-sharing considerations."

### Trade-offs

| Need | Better fit |
|---|---|
| Fast prototype with strongest general reasoning | Proprietary API |
| Sensitive data and local control | Open source/local |
| Narrow supervised task | Open source fine-tuned model |
| Low ML operations burden | Proprietary API |
| Deep customization and inspectable artifacts | Open source |

## 15-Minute Practice Flow

1. Explain the project in one paragraph.
2. Walk through Hugging Face Hub, Datasets, Transformers, PEFT, model cards, and Spaces.
3. Explain PyTorch tensors, device movement, training loop, and inference loop.
4. Explain LoRA, rank, target modules, validation, early stopping, and metrics.
5. Finish with open-source vs proprietary trade-offs using a compliance example.

## Commands to Practice

```bash
python3 scripts/pytorch_basics.py
python3 scripts/train_lora_classifier.py --smoke
python3 scripts/evaluate.py --model-dir outputs/emotion-lora --max-test-samples 128
streamlit run app.py
```

## Fast Spoken Answers

**What did you build?**

I built a Hugging Face and PyTorch fine-tuning lab that trains a LoRA adapter on DistilBERT for emotion classification, evaluates it, documents it with a model card, and serves it locally through Streamlit.

**What is Hugging Face Hub?**

It is a Git-backed platform for models, datasets, Spaces, model cards, and community collaboration. It stores artifacts and versions, not just code snippets.

**What is LoRA?**

LoRA is parameter-efficient fine-tuning. It freezes the base model and trains small low-rank adapter matrices in selected layers, which makes training cheaper and adapter artifacts smaller.

**How do you avoid overfitting?**

Use validation metrics, early stopping, dropout, weight decay, limited epochs, and compare test metrics after training. If the train score rises but validation falls, the model is overfitting.

**Why not always use a proprietary model?**

Proprietary APIs are strong and convenient, but local open-source models offer more control for privacy, compliance, cost predictability, and task-specific customization.
