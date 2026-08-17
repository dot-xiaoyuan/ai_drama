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

## 放角色图片

把角色参考图放到：

```text
characters/hero/
```

支持：

```text
.png
.jpg
.jpeg
.webp
```

Seedance 2.0 系列最多支持 9 张参考图。当前使用官方支持的 base64 data URI 提交本地图片，单张图片限制为 30MB。

## 编辑镜头

编辑：

```text
shots/shot_001/shot.json
```

示例字段：

```json
{
  "id": "shot_001",
  "character": "hero",
  "duration": 5,
  "resolution": "720p",
  "aspect_ratio": "16:9",
  "candidate_count": 1,
  "prompt": "角色走在走廊里，停下并回头。"
}
```

可选字段：

```text
model
seed
movement_amplitude
audio
```

默认模型是 `doubao-seedance-2-0-fast-260128`，默认 `audio=false`。

## 运行

```bash
python main.py generate shot_001
```

流程：

```text
读取镜头配置
读取角色参考图
提交 Seedance 视频生成任务
轮询任务状态
下载 MP4
写入 metadata.json
```

## 查看结果

```text
outputs/shot_001/
```

输出示例：

```text
outputs/shot_001/shot_001_v1.mp4
outputs/shot_001/metadata.json
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
