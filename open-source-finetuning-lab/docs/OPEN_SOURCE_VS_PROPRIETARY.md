# Open Source vs Proprietary LLM Trade-offs

## Interview Position

The choice is not "open-source good, proprietary bad." It is a requirements decision. Proprietary APIs are often best for speed, quality, and managed reliability. Open-source models are often better when privacy, compliance, cost predictability, offline access, or deep customization matter.

## Why Use Open Source Here

- **Privacy and compliance:** sensitive data can stay inside the organization or local machine.
- **Control:** model weights, tokenizer, adapter files, and inference behavior are inspectable.
- **Customization:** LoRA lets us adapt a model to a specific labeled task without training all weights.
- **Cost predictability:** after setup, local inference cost is mostly compute rather than per-token API billing.
- **Portability:** artifacts can run in local notebooks, servers, containers, or Hugging Face Spaces.

## Why Use Proprietary APIs

- **Higher general reasoning quality:** frontier proprietary models often outperform small local models.
- **Managed infrastructure:** no GPU provisioning, patching, autoscaling, or model-serving maintenance.
- **Fast prototyping:** fewer ML engineering steps before the first working result.
- **Tooling maturity:** hosted APIs often include built-in safety, monitoring, batch APIs, and enterprise controls.

## Compliance Example

For HIPAA-like or customer-confidential workflows, sending raw data to an external API may be restricted. In that case, local open-source hosting can reduce third-party exposure. That does not automatically make the system compliant. You still need access controls, audit logs, encryption, data retention policy, model evaluation, and incident response.

## Practical Trade-off Table

| Dimension | Open source/local | Proprietary API |
|---|---|---|
| Data control | Stronger if self-hosted | Depends on vendor contract and settings |
| Startup speed | Slower | Faster |
| Inference quality | Varies by model size/domain | Usually stronger for broad reasoning |
| Cost model | Hardware and operations | Per-token/API billing |
| Fine-tuning | Full control over adapters and weights | Vendor-specific options |
| Governance | You own evaluation and risk controls | Shared with vendor, but still your responsibility |
| Latency | Can be low if close to users | Depends on network and provider |
| Maintenance | You patch and monitor | Vendor handles platform maintenance |

## How This Project Demonstrates the Trade-off

This lab uses a small open-source encoder model for a narrow classification task. That is a good fit because the task is supervised, the labels are clear, and local inference is cheap. It would not be the right choice for broad multi-step reasoning, where a larger proprietary model may be more accurate.
