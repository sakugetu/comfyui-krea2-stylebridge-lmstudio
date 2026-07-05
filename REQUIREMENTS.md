# 必要環境

このワークフローは、単体で完結するワンクリック版ではありません。Krea2のローカル推論、LM Studioによる画像/日本語プロンプト解析、Krea2 NegPiP、Untwisting RoPEによるスタイル参照を組み合わせて使います。

先に、必要なモデル、custom node、LM Studio環境を揃えてください。

## 1. ComfyUI

必要なもの:

- Krea2に対応した比較的新しいComfyUI
- Krea2 / Qwen3-VL系text encoderを動かせるPython環境
- Krea2を動かせるGPUメモリ

ローカル検証で使った構成:

- Krea2 Turbo fp8
- Qwen3-VL text encoder
- Qwen Image VAE

## 2. 同梱custom node

このリポジトリには、次のcustom nodeを同梱しています。

```text
custom_nodes/ComfyUI-Krea2-StyleBridge
```

含まれるノード:

| Node | 役割 |
|---|---|
| `LMStudioPromptControlV4` | 日本語テキストや参照画像をLM Studioへ送り、Krea2向け英語プロンプトを返します |
| `KreaPromptAvoidWeights` | avoid語を `(split screen:-1.00)` のようなKrea2向け負方向ウェイトへ変換します |
| `KreaHighStrengthLoraModelOnly` | 高strength対応のmodel-only LoRA loaderです。`None` pass-throughに対応しています |
| `KreaAspectRatioAreaSizeV2` | 1024 / 1280の基準面積を切り替えられる画角ドロップダウンです |

インストール先:

```text
ComfyUI/custom_nodes/ComfyUI-Krea2-StyleBridge
```

コピー後、ComfyUIを再起動してください。

## 3. 外部custom node

### 必須

| ワークフロー内のNode Type | custom node / source | 必要な理由 |
|---|---|---|
| `ApplyKrea2NegPiP` | `blue-pen5805/ComfyUI-krea2-negpip` | Krea2のプロンプト内で負方向ウェイトを使うため |
| `RFInversion` | `BigStationW/ComfyUi-Untwisting-RoPE` | スタイル参照用のtrajectoryを作るため |
| `UntwistingRoPE` | `BigStationW/ComfyUi-Untwisting-RoPE` | RoPE attention patchingでスタイル参照を反映するため |
| `UnofficialExtensions` | `BigStationW/ComfyUi-Untwisting-RoPE` | ワークフロー内の追加制御に使います |

インストール例:

```bash
cd ComfyUI/custom_nodes
git clone https://github.com/blue-pen5805/ComfyUI-krea2-negpip
git clone https://github.com/BigStationW/ComfyUi-Untwisting-RoPE
```

### Untwisting RoPE用Krea2 adapter

Untwisting RoPEでKrea2を扱うには、Krea2用adapterが必要です。検証環境では、community版の `krea2.py` を次の場所に配置しました。

```text
ComfyUI/custom_nodes/ComfyUi-Untwisting-RoPE/models/krea2.py
```

このadapterがない場合、`UntwistingRoPE` ノード自体は読み込めても、Krea2に正しくpatchできないことがあります。

### 追加の画像読み込みノードについて

公開用ワークフローは、標準の `LoadImage`、`ImageScale`、ComfyUI core nodeを使います。追加の画像loader系custom nodeは不要です。

## 4. モデルファイル

ワークフロー内のモデル名は例です。自分のComfyUI環境にあるファイル名に合わせて、各ノードのドロップダウンを変更してください。

### Diffusion model

例:

```text
models/unet/Krea2/krea2_turbo_fp8_scaled.safetensors
```

使用ノード:

```text
UNETLoader
```

### Text encoder

例:

```text
models/text_encoders/qwen3vl_4b_bf16.safetensors
```

公開ワークフローの既定値:

```text
models/text_encoders/qwen3vl_4b_fp8_scaled.safetensors
```

使用ノード:

```text
CLIPLoader
```

fp8 text encoderが環境によって読めない場合は、bf16のQwen3-VL系text encoderを試してください。

### VAE

例:

```text
models/vae/qwen_image_vae.safetensors
```

使用ノード:

```text
VAELoader
```

### 任意のLoRA

ワークフローには、2つの任意LoRAスロットがあります。

- 任意のuser LoRA
- 任意のKrea2 modifier LoRA / filter bypass LoRA

公開用の初期値はどちらも次です。

```text
None
```

つまり、公開ワークフローはuser LoRAもbypass/modifier LoRAも使わない状態から始まります。LoRAを持っている場合だけ、実ファイル名とstrengthを設定してください。

同梱の `KreaHighStrengthLoraModelOnly` は、`None` をそのまま通すpass-throughに対応しています。古い同名custom nodeを使っていて、ドロップダウンに `None` が出ない場合は、ワークフロー検証で失敗することがあります。その場合は、このリポジトリ同梱版を使うか、既存ノードを `None` 対応版に更新してください。

重要な区別:

- 任意: Krea2 filter bypass / modifier LoRAファイル
- 必須: `ComfyUI-krea2-negpip` custom node

このワークフローは `ApplyKrea2NegPiP` を使うため、bypass LoRAファイルを使わない場合でも `ComfyUI-krea2-negpip` は必要です。

## 5. LM Studio

必要なもの:

- LM Studioがローカルで起動していること
- OpenAI互換API serverが有効になっていること
- 画像を読めるvision対応モデルが読み込まれていること

既定のAPI endpoint:

```text
http://127.0.0.1:1234/v1
```

推奨モデル:

```text
qwen3-vl-32b-instruct
```

小さいvision modelでも動くことはありますが、日本語テキストを無視したり、画像にない内容を発明したりすることがあります。日本語指示が反映されない場合は、`model` 欄で強めのvision modelを明示してください。

## 6. 使用するノード一覧

### ComfyUI core / Krea2系

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

### このリポジトリに同梱

- `LMStudioPromptControlV4`
- `KreaPromptAvoidWeights`
- `KreaHighStrengthLoraModelOnly`
- `KreaAspectRatioAreaSizeV2`

### 外部custom node

- `ApplyKrea2NegPiP`
- `RFInversion`
- `UntwistingRoPE`
- `UnofficialExtensions`

## 7. セットアップ手順

1. ComfyUIをインストールします。
2. Krea2 model、text encoder、VAEを配置します。
3. このリポジトリ同梱の `ComfyUI-Krea2-StyleBridge` custom nodeをインストールします。
4. `ComfyUI-krea2-negpip` をインストールします。
5. `ComfyUi-Untwisting-RoPE` をインストールします。
6. Untwisting RoPEの `models` フォルダへKrea2 adapterを追加します。
7. LM Studioを起動し、vision対応モデルを読み込みます。
8. ComfyUIを起動します。
9. `workflows/krea2_stylebridge_lmstudio_rope_v6_rope_switch.json` を開きます。
10. 画像1/2に内容参照、画像3にスタイル参照を入れます。
11. モデル名のドロップダウンを自分の環境に合わせます。

RoPEスタイル参照を使わない場合は、`Use RoPE style reference switch - OFF skips RoPE branch` の `use_rope_style_reference` をOFFにしてください。OFFの場合、lazy switchによりRoPE側の重い枝は実行されません。

## 8. トラブルシュート

### `LMStudioPromptControlV4` がMissing Nodeになる

このリポジトリ同梱のcustom nodeを `ComfyUI/custom_nodes` に入れて、ComfyUIを再起動してください。

### `ApplyKrea2NegPiP` がMissing Nodeになる

`ComfyUI-krea2-negpip` をインストールしてください。

### `RFInversion` / `UntwistingRoPE` がMissing Nodeになる

`ComfyUi-Untwisting-RoPE` をインストールしてください。

### Untwisting RoPEがKrea2に効かない

Krea2 adapterがあるか確認してください。

```text
ComfyUI/custom_nodes/ComfyUi-Untwisting-RoPE/models/krea2.py
```

### Spatial mismatch errorが出る

Untwisting RoPEでは、スタイル参照画像のlatent sizeと生成latent sizeを合わせる必要があります。このワークフローでは、画像3を選択した出力width / heightへresizeしてからVAE Encodeしています。グラフを改造する場合も、このルールは維持してください。

### LM Studioが日本語テキストを無視する

強めのvision/text modelを使ってください。

```text
qwen3-vl-32b-instruct
```

また、`use_text_prompt` がONになっているか確認してください。

### スタイル参照画像から人物や構図が漏れる

Avoid欄に次のような語を追加してください。

```text
person
woman
girl
human
two people
copied composition from style reference
```

またはRoPE強度を下げてください。

```text
adain_strength: 0.50
low_scale_end: 1.10
blocks: 12-27
```
