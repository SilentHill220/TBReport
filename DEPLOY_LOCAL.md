# 本地部署与基础测试指南

## 一、环境准备

### 1. 安装 Python

确保已安装 Python 3.8+，推荐 3.10 或 3.11。

```bash
python --version
```

### 2. 创建虚拟环境（推荐）

```bash
cd e:\SD\TBReport
python -m venv venv
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

> **说明**：`imgkit` 依赖系统安装的 `wkhtmltoimage`。若未安装，战报会回退到 Markdown 模式，不影响基础功能测试。

---

## 二、测试前配置调整

为避免测试时推送钉钉、触发定时任务，建议先用「最小配置」跑通。

### 1. 关闭钉钉推送

在 `config.json` 中修改：

```json
"dingtalk": {
  "enabled": false,
  ...
}
```

### 2. 关闭定时任务（可选）

```json
"scheduler": {
  "enabled": false,
  ...
}
```

### 3. 补齐 export.projectId（若使用自己的 Teambition 项目）

`export` 中需有 `projectId`，可与 `teambition.project_id` 保持一致：

```json
"export": {
  "projectId": "你的项目ID",
  "tql": "taskLayer IN (0,1,2,3,4,5,6,7,8) ORDER BY isDone ASC, created DESC",
  ...
}
```

> 若继续用当前 config 中的项目 ID，可先不改。

---

## 三、基础功能测试

### 测试 1：单次拉取并分析任务（需有效 Teambition Cookies）

```bash
python main.py --once
```

**预期**：

- 输出「正在获取 Teambition 任务数据」
- 若 Cookies 有效，会拉取 CSV、分析并生成 `./data/summary.json`
- 若 Cookies 过期，会报错，需从浏览器重新获取并更新 `config.json`

### 测试 2：启动 Web 看板（不依赖 Teambition 数据）

```bash
python app.py
```

或使用：

```bash
start_web.bat
```

浏览器访问：`http://localhost:5000`

**说明**：

- 若尚未运行过 `main.py --once`，`./data/summary.json` 可能不存在，看板可能为空或报错
- 可先运行一次 `main.py --once` 生成 `summary.json`，再启动 Web

### 测试 3：仅验证 Web 页面是否能打开

即使没有 `summary.json`，首页 `/` 和部分页面也应能打开，用于确认 Flask 和路由是否正常。

---

## 四、Teambition Cookies 获取（拉取任务必需）

1. 用 Chrome 登录 [Teambition](https://www.teambition.com)
2. 按 F12 打开开发者工具 → Application → Cookies → `https://www.teambition.com`
3. 找到并复制以下 Cookie 值到 `config.json` 的 `teambition.cookies`：
   - `TEAMBITION_SESSIONID`
   - `TEAMBITION_SESSIONID.sig`
   - `TB_ACCESS_TOKEN`

Cookies 会过期，若拉取失败，需重新获取并更新配置。

---

## 五、测试通过后的下一步

- 开启 `dingtalk.enabled` 和钉钉机器人 Webhook，测试推送
- 开启 `scheduler.enabled` 并设置 `scheduler.time`，测试定时战报
- 修改 `dashboard_url` 为实际访问地址（如 `http://你的IP:5000/dashboard`）

---

## 六、常见问题

| 现象 | 可能原因 |
|------|----------|
| 拉取任务失败 | Cookies 过期或 projectId 不正确 |
| 钉钉收不到消息 | `dingtalk.enabled` 为 true 但 webhook/secret 配置有误 |
| 看板为空 | 未生成 `summary.json`，先运行 `main.py --once` |
| `imgkit` 相关报错 | 未安装 wkhtmltoimage，可忽略，会使用 Markdown 模式 |
