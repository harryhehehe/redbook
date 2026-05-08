# 小红书数学家教内容数据结构说明

本目录包含将两份运营方案 docx 结构化后的 JSON 数据，供"自动生成小红书帖子 App"使用。

## 文件清单

| 文件 | 用途 |
|---|---|
| `templates.json` | 7 套帖子骨架模板（block 槽位定义），LLM 按模板填空生成 |
| `posts.json` | 28 篇真实范例帖，带标签，作为 LLM few-shot 示例 + 内容冷启动 |
| `libraries.json` | 可复用素材库：开头钩子 / 互动钩子 / 引流钩子 / Emoji / 分隔符 / 身份金句 |

## 帖子的"积木式"结构

每篇帖子由若干 **block** 顺序拼接而成。模板 = block 序列 + 每个 block 的槽位定义。

### Block 类型字典

| block 类型 | 含义 | 必填槽位 |
|---|---|---|
| `title` | 标题（小红书前 20 字必带钩子） | `text` |
| `opener` | 引入：学生原话 / 家长提问 / 反常识断言 | `style`(student_quote\|parent_question\|bold_claim\|observation), `text` |
| `principle` | 核心原则 / 口诀 / 公式（带 emoji 列表） | `items[]` |
| `case_study` | 真题或学生案例（条件→常规做法→新做法→结果） | `topic`, `condition`, `common_approach`, `new_approach`, `result` |
| `breakdown` | 拆解 N 种类型（粗心的 5 种真面目这种） | `items[]`（每项含 `label`+`detail`+`diagnosis`） |
| `before_after` | 改造前 vs 改造后 / 普通学生 vs 高手 | `before[]`, `after[]` |
| `insight` | 💡关键认知（金句段） | `text` |
| `method` | 我的做法 / 解决方案（步骤型） | `steps[]` |
| `divider` | 分隔符 `——————` | 无 |
| `engagement_hook` | 互动钩子：评论区站队/报数字/聊聊 | `question`, `cta_format`(option\|describe\|number) |
| `lead_magnet` | 引流钩子：回复关键词领资料 | `keyword`, `resource_name`, `resource_desc` |

## 7 套模板（详见 templates.json）

| ID | 名称 | 适用场景 | 系列 |
|---|---|---|---|
| `T1_solution_trick` | 解题神技型 | 学科干货、口诀、真题拆解 | 解题神技 |
| `T2_pain_resonance` | 痛点共鸣型 | 拆解"粗心/假装努力"等高频痛点 | 学习痛点 |
| `T3_counter_intuitive` | 反常识型 | 反对盲目刷题、慢即是快等观点 | 反常识 |
| `T4_parent_qa` | 家长问答型 | 家长私信→3问诊断→方案 | 家长问答 |
| `T5_pick_teacher` | 选老师/避坑型 | 看 N 个细节判断好老师 | 选课避坑 |
| `T6_school_compare` | 学校/政策对比型 | 深圳本地差异、教材改版 | 本地化 |
| `T7_teaching_diary` | 教学日常型 | 学生改造前后、第一节课故事 | 教学日常 |

## 帖子标签（tags）

每篇 `posts.json` 中的帖子带以下标签，便于 App 的检索和推荐：

- `series`: 所属系列
- `template_id`: 对应模板
- `audience`: `student` / `parent` / `both`
- `topics[]`: 学科知识点（如 `几何辅助线`、`二次函数`、`错题本`）
- `pain_points[]`: 涉及的痛点（如 `粗心`、`假装努力`、`补课无效`）
- `region`: 地域标签（如 `深圳`，全国可用为 `null`）
- `grade[]`: 适用年级（`初一`/`初二`/`初三`/`准高一`）
- `hook_type`: 标题钩子类型（`扎心` / `数字` / `疑问` / `反常识` / `身份`）
- `lead_magnet`: 引流资料对象 `{keyword, resource}`

## App 使用建议

**生成流程**：
1. 用户输入主题（如"二次函数"）+ 受众（家长 / 学生）+ 风格偏好
2. 系统从 `posts.json` 检索 2-3 篇匹配标签的范例（few-shot）
3. 选定 `templates.json` 中的一个模板
4. 调用 LLM，prompt = 模板槽位 + few-shot 示例 + `libraries.json` 中的钩子选项
5. LLM 返回 block 化的 JSON，前端按 block 渲染（自动加 emoji、分隔符、空行）
6. 用户在前端微调单个 block，导出为可粘贴的小红书文本
