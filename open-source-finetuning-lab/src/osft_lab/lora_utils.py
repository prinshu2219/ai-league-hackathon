"""LoRA configuration and parameter accounting helpers."""

from typing import Any, Dict, List


def recommended_lora_settings(base_model_name: str) -> Dict[str, Any]:
    model_name = base_model_name.lower()
    if "distilbert" in model_name:
        target_modules: List[str] = ["q_lin", "v_lin"]
    elif "bert" in model_name or "roberta" in model_name:
        target_modules = ["query", "value"]
    else:
        target_modules = ["q_proj", "v_proj"]

    return {
        "r": 8,
        "lora_alpha": 16,
        "lora_dropout": 0.05,
        "target_modules": target_modules,
        "bias": "none",
    }


def trainable_parameter_summary(model: Any) -> Dict[str, float]:
    total_params = 0
    trainable_params = 0

    for _, parameter in model.named_parameters():
        count = parameter.numel()
        total_params += count
        if getattr(parameter, "requires_grad", False):
            trainable_params += count

    frozen_params = total_params - trainable_params
    trainable_percent = 0.0 if total_params == 0 else trainable_params / total_params * 100
    return {
        "total_params": total_params,
        "trainable_params": trainable_params,
        "frozen_params": frozen_params,
        "trainable_percent": round(trainable_percent, 4),
    }


def build_lora_config(config: Any):
    from peft import LoraConfig, TaskType

    settings = recommended_lora_settings(config.base_model_name)
    return LoraConfig(
        task_type=TaskType.SEQ_CLS,
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        target_modules=settings["target_modules"],
        bias=settings["bias"],
    )


def attach_lora_adapter(model: Any, config: Any):
    from peft import get_peft_model

    return get_peft_model(model, build_lora_config(config))
