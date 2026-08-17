# 项目协作说明

这是个人 AI 漫剧生产工作流，不是 SaaS，也不是完整平台。

## 核心原则

1. 不开发 Web UI。
2. 优先保持简单，避免过度工程化。
3. 一个 Shot 是最小生产单位。
4. Provider 应保持可替换，第三方 API 代码集中在独立 client 中。
5. 当前默认 Provider 是 Seedance，Vidu 作为可切换备用 Provider 保留。
6. 不要未经要求加入数据库、Redis、Docker、复杂 ORM、消息队列等组件。
7. 所有第三方 API 实现必须以当前官方文档为准，不凭记忆猜 endpoint、字段名或模型名。
8. API Key 永远不能提交到 Git。
9. 不要修改已经成功生成的视频文件。
10. 后续功能优先在现有架构上渐进增加。
11. Windows 是主要运行环境，命令和路径说明需要兼容 Windows 用户。

## 当前架构

```text
main.py
  -> src/shot_loader.py
  -> src/seedance_client.py
  -> src/vidu_client.py
  -> src/downloader.py
```

Shot 配置位于 `shots/{shot_id}/shot.json`，角色参考图位于 `characters/{character}/`，生成结果写入 `outputs/{shot_id}/`。

## 当前默认 Provider

Seedance 使用火山方舟/BytePlus ModelArk 视频生成 API：

```text
POST {api_base_url}/contents/generations/tasks
GET  {api_base_url}/contents/generations/tasks/{task_id}
Authorization: Bearer {ARK_API_KEY}
```

默认模型：

```text
doubao-seedance-2-0-fast-260128
```

不要把 Seedance 2.0 多参考图工作流退化成 Seedance 1.0 首帧图生视频，除非用户明确要求。

## 第一阶段不做

不要实现 Web UI、账号体系、数据库、权限系统、云部署、Docker、支付、用户管理、自动发布、复杂任务队列、AI 自动评分、自动选择最佳视频、完整剧本拆镜、TTS、字幕、BGM、FFmpeg 成片、ComfyUI API、Kling API。

## Git 提交信息

所有 git commit 提交信息必须使用中文，清楚说明本次改动的核心内容和影响范围。
