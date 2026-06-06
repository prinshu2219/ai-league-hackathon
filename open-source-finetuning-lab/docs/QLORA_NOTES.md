# QLoRA Notes

## What QLoRA Adds

LoRA freezes the base model and trains small low-rank adapter matrices. QLoRA goes further by loading the frozen base model in low-bit quantized form, commonly 4-bit, while training LoRA adapters on top.

## Why It Matters

QLoRA makes it possible to fine-tune much larger models on limited GPU memory. Instead of loading all base weights in full precision, the base model is quantized and only the adapter weights are updated.

## Why This Project Uses LoRA Instead

This project is CPU-first and designed for a reliable L1 interview demo on a local machine. QLoRA usually depends on GPU-oriented quantization libraries such as bitsandbytes, which may not work well on every Mac or CPU-only environment. The project documents QLoRA conceptually and uses standard LoRA for the runnable workflow.

## How to Explain LoRA vs QLoRA

- **LoRA:** freezes the original model and trains small adapter matrices. It reduces trainable parameters.
- **QLoRA:** quantizes the frozen base model, then trains LoRA adapters. It reduces memory usage further.
- **Trade-off:** QLoRA is more memory efficient, but it adds quantization complexity and hardware constraints.

## Interview Answer

"I used LoRA in the project because it is reliable on local hardware and clearly demonstrates parameter-efficient fine-tuning. QLoRA would be the next step if I needed to fine-tune a larger generative model under GPU memory limits. The main difference is that QLoRA stores the frozen base model in low-bit quantized form while still training LoRA adapters."
