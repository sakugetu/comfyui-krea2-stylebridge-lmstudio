from __future__ import annotations

import base64
import io
import json
import math
import urllib.error
import urllib.request

import numpy as np
from PIL import Image

try:
    import folder_paths
except Exception:
    folder_paths = None

try:
    import comfy.sd
    import comfy.utils
except Exception:
    comfy = None


def _image_to_data_url(image, index: int = 0) -> str:
    index = min(max(index, 0), image.shape[0] - 1)
    frame = image[index].detach().cpu().numpy()
    frame = np.clip(frame * 255.0, 0, 255).astype(np.uint8)
    pil_image = Image.fromarray(frame)
    buffer = io.BytesIO()
    pil_image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _clean_prompt(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        text = "\n".join(lines).strip()
    return text.replace("\r\n", "\n").strip()


def _resolve_lmstudio_model(base_url: str, model: str, timeout_seconds: int) -> str:
    model_name = model.strip()
    if model_name.lower() not in {"", "auto", "loaded", "current", "__auto__"}:
        return model_name

    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/models",
        headers={"Content-Type": "application/json"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=min(int(timeout_seconds), 30)) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"LM Studio model auto-select failed HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise RuntimeError(f"LM Studio model auto-select connection failed: {error}") from error

    for item in result.get("data", []):
        candidate = item.get("id") if isinstance(item, dict) else None
        if candidate:
            return str(candidate)
    raise RuntimeError(f"LM Studio model auto-select found no models: {result}")


class LMStudioPromptControlV4:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "use_text_prompt": ("BOOLEAN", {"default": True}),
                "use_image_1": ("BOOLEAN", {"default": False}),
                "use_image_2": ("BOOLEAN", {"default": False}),
                "faithful_image_prompt": ("BOOLEAN", {"default": True}),
                "exclude_style_from_prompt": ("BOOLEAN", {"default": True}),
                "base_url": ("STRING", {"default": "http://127.0.0.1:1234/v1"}),
                "model": ("STRING", {"default": "qwen3-vl-32b-instruct"}),
                "instruction": (
                    "STRING",
                    {
                        "default": (
                            "You are writing a Krea 2 Turbo prompt from enabled user text and image references. "
                            "Follow the two workflow control switches exactly.\n\n"
                            "If faithful_image_prompt is ON, describe the enabled content image references as faithfully as possible: "
                            "subject, pose, expression, clothing, accessories, props, object colors, spatial layout, background objects, location, and framing. "
                            "If faithful_image_prompt is OFF, use the enabled sources as loose inspiration and make a coherent final scene that follows the user text.\n\n"
                            "If exclude_style_from_prompt is ON, do not describe art style, rendering style, medium, artist influence, camera film stock, illustration type, "
                            "model aesthetic, texture treatment, color grading, line art, cel shading, painterly quality, photorealism, anime style, 3D style, cinematic look, "
                            "grain, bokeh, lens effects, lighting treatment, atmosphere, mood, or overall finish. If exclude_style_from_prompt is OFF, you may include visible "
                            "style and finish details from the enabled image references, but keep them concise and do not override the user text.\n\n"
                            "If use_text_prompt is enabled, the user text is mandatory and has highest priority. If the user text is Japanese or another non-English language, "
                            "translate its meaning into natural English and blend it with enabled visual content. If no content image is enabled, expand only the user text and "
                            "do not invent a different main subject.\n\n"
                            "Create one coherent final scene with one subject arrangement, one camera view, and one continuous physical space. Do not mention references as references, "
                            "examples, panels, comparisons, before-and-after views, split screens, collages, or separate sources. Do not invent unrelated objects, extra characters, "
                            "animals, costumes, or backgrounds unless the user text explicitly requests them. Keep clothing dignified and non-revealing.\n\n"
                            "Write one polished English paragraph of 90 to 190 words. No markdown, bullets, labels, explanations, or analysis."
                        ),
                        "multiline": True,
                    },
                ),
                "text_prompt": (
                    "STRING",
                    {"default": "猫が日向ぼっこをしている", "multiline": True},
                ),
                "extra_prompt": (
                    "STRING",
                    {
                        "default": "preserve the visible subject, pose, clothing, props, setting, and spatial layout from the enabled content references",
                        "multiline": True,
                    },
                ),
                "max_tokens": ("INT", {"default": 900, "min": 64, "max": 4096}),
                "temperature": ("FLOAT", {"default": 0.15, "min": 0.0, "max": 2.0, "step": 0.05}),
                "timeout_seconds": ("INT", {"default": 240, "min": 10, "max": 900}),
            },
            "optional": {
                "image_1": ("IMAGE",),
                "image_2": ("IMAGE",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate_prompt"
    CATEGORY = "Krea2 StyleBridge/LLM"

    def generate_prompt(
        self,
        use_text_prompt: bool,
        use_image_1: bool,
        use_image_2: bool,
        faithful_image_prompt: bool,
        exclude_style_from_prompt: bool,
        base_url: str,
        model: str,
        instruction: str,
        text_prompt: str,
        extra_prompt: str,
        max_tokens: int,
        temperature: float,
        timeout_seconds: int,
        image_1=None,
        image_2=None,
    ):
        base_url = base_url.rstrip("/")
        model = _resolve_lmstudio_model(base_url, model, timeout_seconds)
        text_prompt = text_prompt.strip()
        suffix = extra_prompt.strip()

        if use_image_1 and image_1 is None:
            raise RuntimeError("use_image_1 is enabled, but image_1 is not connected.")
        if use_image_2 and image_2 is None:
            raise RuntimeError("use_image_2 is enabled, but image_2 is not connected.")
        if use_text_prompt and not text_prompt:
            raise RuntimeError("use_text_prompt is enabled, but text_prompt is empty.")
        if not use_text_prompt and not use_image_1 and not use_image_2:
            raise RuntimeError("Enable at least one source: text_prompt, image_1, or image_2.")

        enabled = []
        if use_text_prompt:
            enabled.append("text_prompt")
        if use_image_1:
            enabled.append("image_1")
        if use_image_2:
            enabled.append("image_2")

        style_rule = (
            "Style exclusion is ON. Remove style and finish terms from the final prompt; content and composition only."
            if exclude_style_from_prompt
            else "Style exclusion is OFF. You may include concise visible style, finish, lighting, and rendering details from enabled image references."
        )
        fidelity_rule = (
            "Faithful image prompting is ON. Preserve enabled image content details closely unless the user text directly conflicts."
            if faithful_image_prompt
            else "Faithful image prompting is OFF. Use enabled images as flexible inspiration and prioritize a coherent final scene."
        )

        content = [
            {"type": "text", "text": instruction.strip()},
            {"type": "text", "text": f"Enabled sources: {', '.join(enabled)}."},
            {"type": "text", "text": fidelity_rule},
            {"type": "text", "text": style_rule},
        ]

        if use_text_prompt:
            content.append(
                {
                    "type": "text",
                    "text": (
                        "User content request. Translate to natural English if needed and merge it into the final prompt. "
                        "The user text's main subject and action must remain visible: "
                        f"{text_prompt}"
                    ),
                }
            )

        image_extract_tail = (
            "Do not extract style, medium, lighting treatment, texture treatment, atmosphere, or overall finish."
            if exclude_style_from_prompt
            else "You may also extract concise visible style, lighting, color treatment, texture, and finish details."
        )

        if use_image_1:
            content.extend(
                [
                    {
                        "type": "text",
                        "text": (
                            "Reference A visual ingredients. Extract subject, pose, expression, clothing, accessories, props, "
                            "spatial layout, background objects, scene location, framing, and important object colors. "
                            f"{image_extract_tail}"
                        ),
                    },
                    {"type": "image_url", "image_url": {"url": _image_to_data_url(image_1)}},
                ]
            )

        if use_image_2:
            label = (
                "Reference B visual ingredients. Extract complementary subject, pose, expression, clothing, props, setting, "
                "layout, and important object colors, then merge them into one continuous scene. "
                f"{image_extract_tail}"
            )
            if not use_image_1:
                label = (
                    "Reference B visual ingredients, used as the primary visual reference because Reference A is disabled. "
                    "Describe one final scene only. "
                    f"{image_extract_tail}"
                )
            content.extend(
                [
                    {"type": "text", "text": label},
                    {"type": "image_url", "image_url": {"url": _image_to_data_url(image_2)}},
                ]
            )

        if suffix:
            content.append({"type": "text", "text": f"Additional constraints to obey: {suffix}"})

        payload = {
            "model": model.strip(),
            "messages": [{"role": "user", "content": content}],
            "max_tokens": int(max_tokens),
            "temperature": float(temperature),
        }

        request = urllib.request.Request(
            f"{base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=int(timeout_seconds)) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LM Studio HTTP {error.code}: {detail}") from error
        except urllib.error.URLError as error:
            raise RuntimeError(f"LM Studio connection failed: {error}") from error

        try:
            text = result["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError(f"Unexpected LM Studio response: {result}") from error

        prompt = _clean_prompt(text)
        if suffix and suffix.lower() not in prompt.lower():
            prompt = f"{prompt}, {suffix}"
        return (prompt,)


class KreaPromptAvoidWeights:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "base_prompt": ("STRING", {"default": "", "multiline": True}),
                "extra_prompt": ("STRING", {"default": "", "multiline": True}),
                "avoid_prompt": (
                    "STRING",
                    {
                        "default": "split screen\ncollage\ndiptych\ntwo panels\ngrid layout\nduplicate frame",
                        "multiline": True,
                    },
                ),
                "avoid_weight": ("FLOAT", {"default": -1.0, "min": -3.0, "max": 0.0, "step": 0.05}),
            }
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("prompt", "weighted_avoid")
    FUNCTION = "combine"
    CATEGORY = "Krea2 StyleBridge/Prompt"

    def _split_terms(self, text: str):
        terms = []
        for line in str(text or "").replace("、", ",").splitlines():
            for part in line.split(","):
                term = part.strip()
                if term:
                    terms.append(term)
        return terms

    def _weighted_term(self, term: str, weight: float):
        term = term.strip()
        if not term:
            return ""
        if term.startswith("(") and term.endswith(")") and ":" in term:
            return term
        clean = term.strip("() ")
        return f"({clean}:{float(weight):.2f})"

    def combine(self, base_prompt: str, extra_prompt: str, avoid_prompt: str, avoid_weight: float):
        chunks = []
        for text in (base_prompt, extra_prompt):
            text = str(text or "").strip().strip(",")
            if text:
                chunks.append(text)

        weighted = [
            weighted
            for weighted in (self._weighted_term(term, avoid_weight) for term in self._split_terms(avoid_prompt))
            if weighted
        ]
        if weighted:
            chunks.append(", ".join(weighted))
        return (", ".join(chunks), ", ".join(weighted))


class KreaHighStrengthLoraModelOnly:
    def __init__(self):
        self.loaded_lora = None

    @classmethod
    def INPUT_TYPES(cls):
        loras = folder_paths.get_filename_list("loras") if folder_paths is not None else []
        loras = ["None"] + list(loras)
        return {
            "required": {
                "model": ("MODEL",),
                "lora_name": (loras,),
                "strength_model": (
                    "FLOAT",
                    {"default": 1000.0, "min": -40000.0, "max": 40000.0, "step": 1.0},
                ),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "load_lora_model_only"
    CATEGORY = "Krea2 StyleBridge/Krea2"

    def load_lora_model_only(self, model, lora_name, strength_model):
        if comfy is None or folder_paths is None:
            raise RuntimeError("ComfyUI modules are not available for loading LoRA files.")
        if str(lora_name).strip().lower() in {"", "none"} or float(strength_model) == 0.0:
            return (model,)

        lora_path = folder_paths.get_full_path_or_raise("loras", lora_name)
        lora = None
        lora_metadata = None
        if self.loaded_lora is not None:
            if self.loaded_lora[0] == lora_path:
                lora = self.loaded_lora[1]
                lora_metadata = self.loaded_lora[2] if len(self.loaded_lora) > 2 else None
            else:
                self.loaded_lora = None

        if lora is None:
            lora, lora_metadata = comfy.utils.load_torch_file(lora_path, safe_load=True, return_metadata=True)
            self.loaded_lora = (lora_path, lora, lora_metadata)

        model_lora, _ = comfy.sd.load_lora_for_models(
            model, None, lora, float(strength_model), 0.0, lora_metadata=lora_metadata
        )
        return (model_lora,)


class KreaModelRoPESwitchLazy:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "use_rope_style_reference": ("BOOLEAN", {"default": True}),
                "model_without_rope": ("MODEL", {"lazy": True}),
                "model_with_rope": ("MODEL", {"lazy": True}),
            }
        }

    RETURN_TYPES = ("MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "choose"
    CATEGORY = "Krea2 StyleBridge/Krea2"

    def check_lazy_status(self, use_rope_style_reference, model_without_rope=None, model_with_rope=None):
        if use_rope_style_reference and model_with_rope is None:
            return ["model_with_rope"]
        if not use_rope_style_reference and model_without_rope is None:
            return ["model_without_rope"]
        return []

    def choose(self, use_rope_style_reference, model_without_rope, model_with_rope):
        return (model_with_rope if use_rope_style_reference else model_without_rope,)


class KreaAspectRatioAreaSizeV2:
    RATIOS = {
        "1:1 square": (1, 1),
        "16:9 landscape": (16, 9),
        "9:16 vertical": (9, 16),
        "4:3 landscape": (4, 3),
        "3:4 portrait": (3, 4),
        "3:2 landscape": (3, 2),
        "2:3 portrait": (2, 3),
        "21:9 ultrawide": (21, 9),
        "custom": (1, 1),
    }

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "aspect_ratio": (list(cls.RATIOS.keys()), {"default": "1:1 square"}),
                "base_size": (["1280", "1024"], {"default": "1280"}),
                "custom_aspect_width": ("INT", {"default": 1, "min": 1, "max": 1000}),
                "custom_aspect_height": ("INT", {"default": 1, "min": 1, "max": 1000}),
            }
        }

    RETURN_TYPES = ("INT", "INT", "STRING", "INT")
    RETURN_NAMES = ("width", "height", "label", "area")
    FUNCTION = "resolve"
    CATEGORY = "Krea2 StyleBridge/Krea2"

    def resolve(self, aspect_ratio: str, base_size: str, custom_aspect_width: int, custom_aspect_height: int):
        if aspect_ratio == "custom":
            ratio_width = max(1, int(custom_aspect_width))
            ratio_height = max(1, int(custom_aspect_height))
        else:
            ratio_width, ratio_height = self.RATIOS[aspect_ratio]

        base = int(base_size)
        target_area = base * base
        ratio = ratio_width / ratio_height
        width = max(64, int(round(math.sqrt(target_area * ratio) / 8)) * 8)
        height = max(64, int(round(math.sqrt(target_area / ratio) / 8)) * 8)
        area = width * height
        return (width, height, f"{aspect_ratio} base={base} {width}x{height} area={area}", area)


NODE_CLASS_MAPPINGS = {
    "LMStudioPromptControlV4": LMStudioPromptControlV4,
    "KreaPromptAvoidWeights": KreaPromptAvoidWeights,
    "KreaHighStrengthLoraModelOnly": KreaHighStrengthLoraModelOnly,
    "KreaModelRoPESwitchLazy": KreaModelRoPESwitchLazy,
    "KreaAspectRatioAreaSizeV2": KreaAspectRatioAreaSizeV2,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "LMStudioPromptControlV4": "LM Studio Prompt Control V4 Faithful/NoStyle",
    "KreaPromptAvoidWeights": "Krea Prompt + Avoid (-weights)",
    "KreaHighStrengthLoraModelOnly": "Krea High Strength LoRA Model Only",
    "KreaModelRoPESwitchLazy": "Krea Model RoPE Switch Lazy",
    "KreaAspectRatioAreaSizeV2": "Krea Aspect Ratio Size by Base Switch",
}
