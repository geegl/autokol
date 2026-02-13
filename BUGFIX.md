# BugFix 记录

本文档记录线上出现过的关键问题、根因与修复状态，便于回溯。

## 2026-02 稳定性修复批次

### 1) 模板预览报错 `Template Error: 'calendly_link'`

- 症状: 不选模板也可能在预览区直接报错，发送测试邮件同样受影响。
- 根因: 模板 `format` 时没有传入 `{calendly_link}`。
- 修复:
  - 统一模板渲染入口，补齐 `calendly_link`/`tracking_pixel`。
  - 模板变量提示同步更新。
- 影响文件:
  - `src/ui/mode_handler.py`

### 2) 模板保存/读取出现递归崩溃 `RecursionError`

- 症状: 保存模板时堆栈反复进入 `load_user_templates` / `save_user_template`。
- 根因: 历史代码中存在相互调用链，且缺少结构校验。
- 修复:
  - 模板读取增加类型校验和默认回退。
  - 写入走内部保存函数，避免递归调用链。
- 影响文件:
  - `src/utils/template_manager.py`

### 3) 通用表格映射后报 `KeyError: 'Name/Institution'`

- 症状: 预览行选择或展示时直接崩溃。
- 根因: 预览标签硬取映射列，未处理“映射列不存在/变更”。
- 修复:
  - 预览标签改为容错逻辑，优先映射列，缺失时自动回退可用字段。
- 影响文件:
  - `src/ui/mode_handler.py`

### 4) 云端模板/发送历史无法同步

- 症状: Streamlit 重启后模板或发送记录丢失。
- 根因: Vercel `api/progress` 仅允许 `B2B/B2C`，拒绝 `user_templates/send_history`。
- 修复:
  - 扩展 `mode` 白名单支持四种模式。
- 影响文件:
  - `email-tracker/api/progress.js`

### 5) 进度回到旧行数（如 41 行覆盖 162 行）

- 症状: 上传新表后仍弹出“继续上次任务”，误读旧进度。
- 根因:
  - 历史进度与当前文件不一致时，缺少自动判定机制。
  - 进度 CSV 曾被纳入仓库，部署后可能带入旧快照。
- 修复:
  - 增加“行数+列重叠”自动判定，不一致时强制 `restart`。
  - 进度 CSV 改为忽略，不再进入 Git。
- 影响文件:
  - `src/ui/mode_handler.py`
  - `.gitignore`

### 6) 云端读取 401 提示误报

- 症状: 页面显示 `PROGRESS_API_KEY 与 Vercel 不匹配（401）`，但接口可用。
- 根因: 使用 fallback key 返回 200 且 `data:null` 时，逻辑仍继续走 401 提示分支。
- 修复:
  - `helpers/template_manager/send_history` 统一双 key 重试。
  - 200 + 空数据直接返回，不再误报 401。
  - API 端支持 fallback key 校验。
- 影响文件:
  - `src/utils/helpers.py`
  - `src/utils/template_manager.py`
  - `src/services/send_history.py`
  - `email-tracker/api/progress.js`

### 7) 切换预览行后已生成内容被清空

- 症状: 先批量生成，再切换 lead 预览，`AI_Project_Title/AI_Technical_Detail` 突然变空。
- 根因: rerun 时重新读取原始 Excel，未优先使用当前会话中的已生成数据。
- 修复:
  - 增加会话级 `working_df` 缓存。
  - 以数据源指纹控制缓存刷新，只有换文件才清缓存。
  - 在编辑、生成、发送等关键节点同步更新缓存。
- 影响文件:
  - `src/ui/mode_handler.py`

## 快速自检清单

1. 预览区是否还能出现 `Template Error`。
2. 上传新表后是否仍会自动继承旧任务。
3. 切换预览行后已生成字段是否稳定保留。
4. `api/progress` 是否能处理 `user_templates/send_history`。
5. Gmail 发送失败是否为认证类错误（`535`）。
