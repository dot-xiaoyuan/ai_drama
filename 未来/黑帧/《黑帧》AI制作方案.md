# 《黑帧》AI 制作方案

## 项目定位

《黑帧》是 9 分钟写实电影感 AI 短片。它不是连续剧，也不是爽剧，而是高概念软科幻情感短片。

核心制作目标：让观众先被“世界每隔一段时间会黑一帧”吸引，最后被“我宁愿痛，也不愿把你从我的人生里剪掉”击中。

## Seedance 2.0 生成原则

1. 每条视频素材按 5 秒生成，最终剪辑可只使用 2～4 秒。
2. 正常现实片段交给 Seedance 生成。
3. 纯黑帧不交给 Seedance，后期直接切黑。
4. 黑帧内的静止世界优先用前一帧冻结、降饱和、加冷色和遮罩完成。
5. 剪辑员只在少量关键镜头中生成或后期合成，不做怪物化真人。
6. 所有文字、手机屏幕、备忘录、照片文字、字幕全部后期叠加。
7. 镜头主角色写在 `character`，同时出现许知遥或剪辑员时，用 `reference_characters` 补充参考图，保证 Seedance 2.0 多参考图一致性。
8. 每个镜头的角色图、额外角色图、场景图总数控制在 9 张以内；多角色镜头优先保留正脸、半身、场景母图，其他角度放到后续补拍。

## 角色参考图清单

### 林默 `characters/lin_mo/`

- `front.png`：27 岁东亚男性，普通白领，清瘦，黑色短发，疲惫但干净，白衬衫或浅色通勤衬衫，写实电影感。
- `side.png`：同一角色侧面，神情克制，适合黑帧观察镜头。
- `closeup.png`：面部特写，眼神敏感，有轻微黑眼圈，不要夸张表情。

参考图生成提示词：

完整生成提示词见：`characters/lin_mo/reference_prompt.md`

### 许知遥 `characters/xu_zhiyao/`

- `front.png`：26 岁东亚女性，温柔但不甜腻，黑色中长发，米白针织或浅色外套。
- `flower_shop.png`：抱着白色郁金香的花店门口形象。
- `memory_closeup.png`：黑帧记忆中的近景，低饱和、柔软、像被找回的照片。

参考图生成提示词：

完整生成提示词见：`characters/xu_zhiyao/reference_prompt.md`

### 剪辑员 `characters/editor_silhouette/`

- `silhouette.png`：负空间人形轮廓，像从胶片上剪下来的空洞。
- `hand_tool.png`：剪刀与时间轴混合的抽象工具。

参考图生成提示词：

完整生成提示词见：`characters/editor_silhouette/reference_prompt.md`

## 场景参考图清单

### 林默家 `scenes/black_frame_home/`

需要卧室、客厅、餐桌、衣柜四类图。整体冷清、真实、普通城市租住房，不要豪宅。

完整生成提示词见：`scenes/black_frame_home/reference_prompt.md`

### 十字路口 `scenes/black_frame_crosswalk/`

完整生成提示词见：`scenes/black_frame_crosswalk/reference_prompt.md`

### 办公室 `scenes/black_frame_office/`

完整生成提示词见：`scenes/black_frame_office/reference_prompt.md`

### 餐厅 `scenes/black_frame_restaurant/`

完整生成提示词见：`scenes/black_frame_restaurant/reference_prompt.md`

### 花店 `scenes/black_frame_flower_shop/`

完整生成提示词见：`scenes/black_frame_flower_shop/reference_prompt.md`

### 黑帧空间 `scenes/black_frame_void/`

完整生成提示词见：`scenes/black_frame_void/reference_prompt.md`

## 黑帧后期规范

- 切黑时长：0.4～2 秒，根据剧情强度变化。
- 声音：黑帧前 0.1 秒抽掉环境声，只留极薄胶片转动底噪。
- 画面：黑帧中使用静帧冻结 + 降饱和 + 冷色 + 局部遮罩。
- 观众第一次理解黑帧时，不解释太多，让画面自己说明。
- 最终高潮黑帧可以更长，但不要做成动作大片。

## 小样优先级

先生成 3 个测试素材：

1. `black_frame/s02_shot_01`：十字路口现实片段。
2. `black_frame/s06_shot_01`：花店空洞片段。
3. `black_frame/s13_shot_06`：最终黑帧中林默伸手抓住记忆。

三个小样通过后，再批量生成其余镜头。
