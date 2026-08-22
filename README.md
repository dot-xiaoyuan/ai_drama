# AI Drama

个人 AI 漫剧镜头生成工作流 POC。第一阶段只验证一件事：读取本地 Shot 配置和角色参考图，调用视频生成 Provider，轮询任务，并把生成 MP4 下载到本地。

当前默认 Provider 是火山方舟 Seedance。Vidu 客户端保留，但默认不使用。

不包含 Web UI、数据库、Docker、队列、TTS、字幕、BGM 成片等平台功能。

## 安装

推荐先创建虚拟环境：

```bash
python -m venv .venv
.venv\Scripts\activate
```

macOS/Linux：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

Windows 环境建议使用 Python 3.11+。

## API Key

复制环境变量模板：

```bash
copy .env.example .env
```

macOS/Linux 可用：

```bash
cp .env.example .env
```

默认使用 Seedance，请填写：

```text
ARK_API_KEY=
```

如果切回 Vidu，再填写：

```text
VIDU_API_KEY=
```

`.env` 已加入 `.gitignore`，不要提交 API Key。

## 资产准备

### 1. 角色参考图
把角色参考图放到：

```text
characters/hero/
```

支持 `.png`、`.jpg`、`.jpeg`、`.webp`。例如：`closeup.png`（半身/特写）、`front.png`（正面全身）、`side.png`（侧面全身）。

### 2. 场景母图库
把高频复用的场景母图放到：

```text
scenes/
```

例如：`office_night.png`（深夜办公室）、`vending_area_night.png`（深夜售货机）、`subway_exit_c.png`（地铁口长椅）、`apartment.png`（出租屋）。

## 镜头配置

支持按分集结构组织：

```text
shots/ep01/shot_01/shot.json
```

示例配置：

```json
{
  "id": "ep01/shot_01",
  "character": "hero",
  "reference_characters": ["supporting_character"],
  "scene": "office_night",
  "duration": 5,
  "resolution": "720p",
  "aspect_ratio": "9:16",
  "candidate_count": 1,
  "prompt": "同一个年轻男性角色在深夜昏暗的现代办公室工位上..."
}
```

- 当配置 `scene` 时，系统会自动将角色图 + 场景母图打包作为 Seedance 2.0 多参考图一同提交。
- 当同一镜头需要多个固定角色时，用 `reference_characters` 补充额外角色目录；主角色仍写在 `character`。
- 当需要精确控制某个镜头使用哪些参考图时，用 `reference_images` 写入图片路径白名单；此时系统只加载这些图片。
- 单个镜头的角色图、额外角色图、场景图总数不能超过 `max_reference_images`。

## 运行与预检

### 1. 预检配置与参考图（不消耗额度）
```bash
python main.py generate ep01/shot_01 --dry-run
```

### 2. 正式调用生成
```bash
python main.py generate ep01/shot_01
```

流程：
```text
读取镜头配置与场景关联
加载角色参考图 + 场景母图并完成 base64 编码
提交 Seedance 视频生成任务
轮询任务状态
下载 MP4 至 outputs/ep01/shot_01/
写入 metadata.json
```

## 查看结果

```text
outputs/ep01/shot_01/
```

输出示例：
```text
outputs/ep01/shot_01/ep01_shot_01_v1.mp4
outputs/ep01/shot_01/metadata.json
```

如果 `candidate_count` 大于 1，会依次创建多个独立任务。某个 candidate 失败不会删除已成功的视频。

## Seedance API 依据

当前 Seedance 实现依据官方文档：

- Base URL and authentication: https://docs.byteplus.com/en/docs/ModelArk/1298459
- Create a video generation task: https://docs.byteplus.com/en/docs/ModelArk/1520757
- Retrieve a video generation task: https://docs.byteplus.com/en/docs/ModelArk/1521309
- Model list: https://docs.byteplus.com/en/docs/ModelArk/1330310

当前使用接口：

```text
POST {api_base_url}/contents/generations/tasks
GET  {api_base_url}/contents/generations/tasks/{task_id}
```

火山方舟中国区默认：

```text
https://ark.cn-beijing.volces.com/api/v3
```

BytePlus 国际区可改为：

```text
https://ark.ap-southeast.bytepluses.com/api/v3
```

认证方式：

```text
Authorization: Bearer {ARK_API_KEY}
```

## 配置

`config/settings.json`：

```json
{
  "provider": "seedance",
  "api_base_url": "https://ark.cn-beijing.volces.com/api/v3",
  "default_model": "doubao-seedance-2-0-fast-260128",
  "poll_interval_seconds": 8,
  "task_timeout_seconds": 900,
  "max_reference_images": 9,
  "max_reference_image_bytes": 31457280
}
```

## 常见错误

没有 API Key：

```text
ARK_API_KEY 未配置，请在 .env 中填写火山方舟/BytePlus ModelArk API Key。
```

没有角色参考图：

```text
角色 hero 没有参考图片。请把 png/jpg/jpeg/webp 放到 characters/hero
```

模型未开通或余额不足时，Seedance API 会返回 401/403/400/402 等错误。程序会输出 HTTP Status、API error code 和 API error message，但不会打印 API Key。

## 切回 Vidu

如需切回 Vidu，把 `config/settings.json` 改成：

```json
{
  "provider": "vidu",
  "api_base_url": "https://api.vidu.cn",
  "default_model": "viduq3-turbo",
  "poll_interval_seconds": 8,
  "task_timeout_seconds": 900,
  "max_reference_images": 7,
  "max_reference_image_bytes": 10485760
}
```
