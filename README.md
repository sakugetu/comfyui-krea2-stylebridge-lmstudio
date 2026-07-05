# Krea2 StyleBridge for ComfyUI

Krea2 StyleBridge is an unofficial ComfyUI workflow that separates **what to draw** from **how it should look**.

日本語の指示文や参照画像を LM Studio で Krea 2 向けの英語プロンプトにまとめ、別のスタイル参照画像を Untwisting RoPE / RF Inversion 経由で Krea 2 に渡すためのワークフローです。

## 何ができるか

- 日本語テキストを LM Studio で英語の Krea 2 向けプロンプトに変換する
- 画像1/画像2を LM Studio に読ませて、内容だけをプロンプト化する
- 画像3をスタイル参照として使い、画風や塗りを RoPE 側で反映する
- 「画像を忠実にプロンプト化するか」を切り替える
- 「画風をLM Studioのプロンプトに入れないか」を切り替える
- Krea2 NegPiP 用の Avoid 語を `(term:-1.00)` 形式で統合する
- 1024 / 1280 相当の面積を保ったまま、画角プリセットを切り替える
- 任意の Krea2 LoRA / modifier LoRA を追加する

公開用の初期状態では、LoRAとfilter bypass系LoRAはどちらも `None` / `0.0` です。必要な人だけ後から選択してください。

`None` は同梱の `KreaHighStrengthLoraModelOnly` が処理します。古い同名ノードを別のcustom nodeから使っている環境では、`None` が選択肢に出ずエラーになることがあります。その場合は、このリポジトリ同梱のcustom nodeを使うか、既存ノードを `None` pass-through 対応版に更新してください。

## ワークフロー名

**Krea2 StyleBridge for ComfyUI**

おすすめの使い方は次の分離です。

- 画像1: 内容参照、主体や構図
- 画像2: 内容参照、混ぜたい要素
- 画像3: スタイル参照、絵柄や塗り
- 日本語テキスト: 追加したい内容指示

同じ画像を内容解析にもスタイル参照にも使いたい場合は、画像1/2と画像3に同じ画像を入れてください。

## 同梱ファイル

```text
workflows/krea2_stylebridge_lmstudio_rope_v6_rope_switch.json
custom_nodes/ComfyUI-Krea2-StyleBridge/
```

`custom_nodes/ComfyUI-Krea2-StyleBridge` には、このワークフロー用の最小ノードが入っています。

- `LMStudioPromptControlV4`
- `KreaPromptAvoidWeights`
- `KreaHighStrengthLoraModelOnly`
- `KreaAspectRatioAreaSizeV2`

## 必要なもの

このリポジトリだけでは完結しません。詳しい要件は [REQUIREMENTS.md](REQUIREMENTS.md) を見てください。

概要として、以下が必要です。

- ComfyUI
- Krea 2 / Krea 2 Turbo 系のローカルモデル
- Krea2 用 text encoder
- Qwen Image VAE など、Krea2環境で使うVAE
- LM Studio
- 画像を読めるLM Studioモデル
  - 例: `qwen3-vl-32b-instruct`
- [ComfyUI-krea2-negpip](https://github.com/blue-pen5805/ComfyUI-krea2-negpip)
- [ComfyUi-Untwisting-RoPE](https://github.com/BigStationW/ComfyUi-Untwisting-RoPE)
- Krea2 用 Untwisting RoPE adapter

Untwisting RoPE 側は、Krea2対応adapterが必要です。環境によってはコミュニティ配布の `models/krea2.py` を追加する必要があります。

## インストール

1. このリポジトリを clone します。

```bash
git clone https://github.com/<your-name>/comfyui-krea2-stylebridge-lmstudio.git
```

2. custom node を ComfyUI にコピーします。

```text
ComfyUI/custom_nodes/ComfyUI-Krea2-StyleBridge
```

3. workflow を ComfyUI の workflow フォルダ、または任意の場所にコピーします。

```text
workflows/krea2_stylebridge_lmstudio_rope_v6_rope_switch.json
```

4. ComfyUI を再起動します。

5. LM Studio を起動し、OpenAI互換APIを有効にします。

既定値:

```text
http://127.0.0.1:1234/v1
```

## 基本操作

最初に、以下のモデル名を自分の環境に合わせてください。

- Krea2 diffusion model
- Krea2 text encoder
- VAE

公開workflowのtext encoder既定値は次です。

```text
qwen3vl_4b_fp8_scaled.safetensors
```

### 日本語テキストを使う

`text_prompt` に日本語で入力します。

例:

```text
猫が日向ぼっこをしている
```

`use_text_prompt` を ON にすると、その文を LM Studio が英語のKrea向けプロンプトに変換します。

`use_text_prompt` を OFF にすると、テキスト欄は無視されます。

### 画像1/画像2を使う

`use_image_1` / `use_image_2` を ON にすると、画像1/画像2が LM Studio に送られます。

画像1は主参照、画像2は補助参照として扱われます。

### スタイル参照を使う

画像3にスタイル参照画像を入れます。

画像3は LM Studio ではなく、RF Inversion / Untwisting RoPE 側に送られます。  
そのため、画像3の画風を使いながら、画像1/画像2や日本語テキストの内容を描くことができます。

## 重要なスイッチ

### faithful_image_prompt

画像1/画像2をどれくらい忠実にプロンプト化するかを決めます。

ON:

```text
画像の主体、服、ポーズ、背景、構図をできるだけ忠実に説明する
```

OFF:

```text
画像はゆるい参考として扱い、最終絵として自然な内容にまとめる
```

### exclude_style_from_prompt

LM Studioのプロンプトに画風語を入れるかどうかを決めます。

ON:

```text
画風、写真風、アニメ風、線画、塗り、質感、シネマティック、ボケなどをプロンプトに入れない
```

画像3のRoPEスタイル参照を主役にしたい場合はこちらがおすすめです。

OFF:

```text
画像1/画像2から見える画風や仕上げも短く入れてよい
```

画像1/画像2そのものの雰囲気までプロンプト化したい場合はこちらです。

## RoPE設定の目安

`Use RoPE style reference switch - OFF skips RoPE branch` の `use_rope_style_reference` をOFFにすると、`RFInversion` / `UntwistingRoPE` / 画像3のVAE Encode枝をlazy評価でスキップします。スタイル参照を使わない通常生成ではOFFにすると速くなります。

控えめ:

```text
blocks: 10-27
adain_strength: 0.65
low_scale_end: 1.20
beta: 3.0
```

スタイル強め:

```text
blocks: 7-27
adain_strength: 0.75
low_scale_end: 1.35
beta: 3.0
```

内容保持寄り:

```text
blocks: 12-27
adain_strength: 0.50
low_scale_end: 1.10
beta: 3.5
```

## Avoid / NegPiP

Krea2では通常のネガティブプロンプトが弱い場合があります。  
このワークフローでは `KreaPromptAvoidWeights` でAvoid語を `(term:-1.00)` 形式に変換し、ポジティブプロンプト側へ統合します。

注意: filter bypass / modifier LoRA は任意ですが、`ApplyKrea2NegPiP` ノード自体はworkflow内で使っています。`ComfyUI-krea2-negpip` はインストールしてください。

例:

```text
split screen
diptych
two panels
copied composition from style reference
unwanted second character
person
woman
girl
```

人物のスタイル参照から猫などを出す場合、人物が漏れることがあります。  
その場合は Avoid に `person`, `woman`, `girl`, `human` などを足してください。

## よくある問題

### スタイル参照画像の構図までコピーされる

RoPEが強すぎます。

- `adain_strength` を下げる
- `low_scale_end` を下げる
- `blocks` を `12-27` など後段寄りにする
- スタイル画像を顔・髪・塗りなどにクロップする

### 画像3のスタイルが弱い

RoPEを少し強めます。

- `adain_strength` を上げる
- `low_scale_end` を上げる
- `blocks` を `7-27` にする

### LM Studioが日本語を無視する

`model` を明示してください。

おすすめ:

```text
qwen3-vl-32b-instruct
```

また、`use_text_prompt` が ON になっているか確認してください。

### Missing Node が出る

以下のcustom nodeが不足している可能性があります。

- `ComfyUI-Krea2-StyleBridge`
- `ComfyUI-krea2-negpip`
- `ComfyUi-Untwisting-RoPE`

## 注意

このリポジトリは非公式です。Krea公式のAPI/Partner Nodeのstyle referenceとは別物で、ローカルComfyUI上での実験的なスタイル参照ワークフローです。

## License

MIT
