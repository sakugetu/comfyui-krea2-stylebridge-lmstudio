# Requirements

This workflow is not a one-click standalone package. It combines Krea2 local inference, LM Studio vision prompting, Krea2 NegPiP, and Untwisting RoPE style transfer.

このワークフローは単体では完結しません。必要なモデル、custom node、LM Studio環境を先に揃えてください。

## 1. ComfyUI

Required:

- Recent ComfyUI build with Krea2 support
- Python environment that can run Krea2 / Qwen3-VL text encoder
- GPU memory appropriate for Krea2

Tested locally with:

- Krea2 Turbo fp8
- Qwen3-VL / Huihui-Qwen3-VL text encoder
- Qwen Image VAE

## 2. Included custom node

This repository includes:

```text
custom_nodes/ComfyUI-Krea2-StyleBridge
```

It provides:

| Node | Purpose |
|---|---|
| `LMStudioPromptControlV4` | Sends Japanese/text and optional image references to LM Studio and returns a Krea2 prompt |
| `KreaPromptAvoidWeights` | Converts avoid terms into Krea-style prompt weights such as `(split screen:-1.00)` |
| `KreaHighStrengthLoraModelOnly` | Optional model-only LoRA loader with a large strength range and `None` pass-through |
| `KreaAspectRatioAreaSizeV2` | Aspect ratio dropdown with 1024 / 1280 base-area switch |

Install it into:

```text
ComfyUI/custom_nodes/ComfyUI-Krea2-StyleBridge
```

Then restart ComfyUI.

## 3. External custom nodes

### Required

| Node Type in Workflow | Custom Node / Source | Why |
|---|---|---|
| `ApplyKrea2NegPiP` | `blue-pen5805/ComfyUI-krea2-negpip` | Enables negative prompt weights inside the Krea2 prompt |
| `RFInversion` | `BigStationW/ComfyUi-Untwisting-RoPE` | Builds the style/reference trajectory |
| `UntwistingRoPE` | `BigStationW/ComfyUi-Untwisting-RoPE` | Applies the style reference through RoPE attention patching |
| `UnofficialExtensions` | `BigStationW/ComfyUi-Untwisting-RoPE` | Optional controls used by the workflow |

Install:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/blue-pen5805/ComfyUI-krea2-negpip
git clone https://github.com/BigStationW/ComfyUi-Untwisting-RoPE
```

### Krea2 adapter for Untwisting RoPE

Untwisting RoPE needs a Krea2 adapter file. In the tested setup, a community `krea2.py` adapter was placed here:

```text
ComfyUI/custom_nodes/ComfyUi-Untwisting-RoPE/models/krea2.py
```

Without this adapter, `UntwistingRoPE` may load but will not patch Krea2 correctly.

### Optional but useful

The public workflow uses standard `LoadImage`, `ImageScale`, and ComfyUI core nodes. It does not require extra image-loader nodes.

## 4. Model files

You need to have equivalent model files in your ComfyUI model folders. Names in the workflow are examples; change dropdowns to match your local files.

### Diffusion model

Example:

```text
models/unet/Krea2/krea2_turbo_fp8_scaled.safetensors
```

Node:

```text
UNETLoader
```

### Text encoder

Examples:

```text
models/text_encoders/qwen3vl_4b_bf16.safetensors
models/text_encoders/Huihui-Qwen3-VL-4B-Instruct-abliterated-fp8_scaled.safetensors
```

Public workflow default:

```text
models/text_encoders/qwen3vl_4b_fp8_scaled.safetensors
```

Node:

```text
CLIPLoader
```

If an fp8 text encoder fails to load in your environment, try a bf16 Qwen3-VL text encoder.

### VAE

Example:

```text
models/vae/qwen_image_vae.safetensors
```

Node:

```text
VAELoader
```

### Optional LoRAs

The workflow has two optional LoRA slots:

- Optional user LoRA
- Optional Krea2 modifier LoRA / filter bypass

Both default to:

```text
None
```

This means the public workflow starts with no user LoRA and no bypass/modifier LoRA. Set a real LoRA name and strength only if you have the LoRA installed.

The included `KreaHighStrengthLoraModelOnly` node supports `None` as a pass-through value. If you already have an older custom node with the same class name and `None` is not available in the dropdown, the workflow can fail validation. Use the included node or update the older node to support `None`.

Important distinction:

- Optional: Krea2 filter bypass / modifier LoRA file
- Required: `ComfyUI-krea2-negpip` custom node, because the workflow uses `ApplyKrea2NegPiP`

## 5. LM Studio

Required:

- LM Studio running locally
- OpenAI-compatible server enabled
- A vision-capable model loaded

Default API endpoint:

```text
http://127.0.0.1:1234/v1
```

Recommended model:

```text
qwen3-vl-32b-instruct
```

Smaller vision models can work, but may ignore Japanese text or invent unrelated content. If Japanese text is not reflected, explicitly select a stronger model in the `model` field.

## 6. Workflow node types

The workflow uses these node types:

### ComfyUI core / Krea2 nodes

- `LoadImage`
- `ImageScale`
- `UNETLoader`
- `CLIPLoader`
- `VAELoader`
- `VAEEncode`
- `VAEDecode`
- `CLIPTextEncode`
- `EmptyLatentImage`
- `KSampler`
- `SaveImage`
- `Note`

### Included in this repository

- `LMStudioPromptControlV4`
- `KreaPromptAvoidWeights`
- `KreaHighStrengthLoraModelOnly`
- `KreaAspectRatioAreaSizeV2`

### External

- `ApplyKrea2NegPiP`
- `RFInversion`
- `UntwistingRoPE`
- `UnofficialExtensions`

## 7. Common setup checklist

1. Install ComfyUI.
2. Install Krea2 model, text encoder, and VAE.
3. Install this repository's `ComfyUI-Krea2-StyleBridge` custom node.
4. Install `ComfyUI-krea2-negpip`.
5. Install `ComfyUi-Untwisting-RoPE`.
6. Add the Krea2 adapter under Untwisting RoPE's `models` folder.
7. Start LM Studio and load a vision-capable model.
8. Start ComfyUI.
9. Open `workflows/krea2_stylebridge_lmstudio_rope_v4.json`.
10. Select image 1/2 for content and image 3 for style.
11. Adjust model dropdowns to your local file names.

## 8. Troubleshooting

### Missing node: `LMStudioPromptControlV4`

Install this repository's custom node and restart ComfyUI.

### Missing node: `ApplyKrea2NegPiP`

Install `ComfyUI-krea2-negpip`.

### Missing node: `RFInversion` / `UntwistingRoPE`

Install `ComfyUi-Untwisting-RoPE`.

### Untwisting RoPE does not affect Krea2

Check that the Krea2 adapter exists:

```text
ComfyUI/custom_nodes/ComfyUi-Untwisting-RoPE/models/krea2.py
```

### Spatial mismatch error

Untwisting RoPE requires the style reference latent size to match the generated latent size. This workflow resizes image 3 to the chosen output width and height before VAE encoding. If you modify the graph, keep this rule.

### LM Studio ignores Japanese text

Use a stronger vision/text model such as:

```text
qwen3-vl-32b-instruct
```

Also check that `use_text_prompt` is ON.

### Style reference leaks unwanted people or layout

Add avoid terms:

```text
person
woman
girl
human
two people
copied composition from style reference
```

Or reduce RoPE strength:

```text
adain_strength: 0.50
low_scale_end: 1.10
blocks: 12-27
```
