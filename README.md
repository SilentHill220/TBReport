# Teambition 任务数据获取和汇总工具

这是一个用于定时获取 Teambition 项目任务数据并汇总分析的工具，可以查看每个人当前挂载的任务。

## 功能特性

- 定时从 Teambition API 获取任务数据（CSV 格式）
- 自动解析和分析任务数据
- 按人员、状态、优先级汇总任务
- 支持定时任务调度
- 生成 JSON 格式的汇总报告

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置说明

在使用前，需要配置 `config.json` 文件：

### 1. 配置 Teambition Cookies

从浏览器中获取 Teambition 的登录 cookies，填入 `teambition.cookies` 字段。

主要需要的 cookies：
- `TEAMBITION_SESSIONID`
- `TEAMBITION_SESSIONID.sig`
- `TB_ACCESS_TOKEN`
- 其他 cookies

### 2. 配置项目信息

- `teambition.project_id`: 你的 Teambition 项目 ID
- `teambition.api_url`: API 地址（一般不需要修改）

### 3. 配置导出参数

- `export.tql`: 任务查询语句
- `export.fileType`: 导出格式（csv）
- `export.scope`: 导出范围

### 4. 配置定时任务

- `scheduler.enabled`: 是否启用定时任务
- `scheduler.interval_minutes`: 执行间隔（分钟）

### 5. 配置输出路径

- `output.csv_dir`: CSV 文件保存目录
- `output.summary_file`: 汇总文件保存路径

## 使用方法

### 单次执行

```bash
python main.py --once
```

### 定时执行（默认每 30 分钟）

```bash
python main.py
```

### 自定义执行间隔

```bash
python main.py --interval 60
```

### 指定配置文件

```bash
python main.py --config my_config.json
```

## 输出文件

- CSV 文件：保存在 `./data/` 目录，文件名格式为 `tasks_YYYYMMDD_HHMMSS.csv`
- 汇总文件：保存在 `./data/summary.json`

## 汇总报告格式

```json
{
  "total_tasks": 100,
  "updated_at": "2025-12-26T10:30:00",
  "by_status": {
    "进行中": 50,
    "已完成": 40,
    "待处理": 10
  },
  "by_priority": {
    "高": 20,
    "中": 60,
    "低": 20
  },
  "by_user": {
    "张三": {
      "name": "张三",
      "total_tasks": 10,
      "tasks": [
        {
          "id": "xxx",
          "title": "任务标题",
          "status": "进行中",
          "priority": "高",
          "created": "2025-12-01",
          "due": "2025-12-31"
        }
      ]
    }
  }
}
```

## 注意事项

1. Cookies 有有效期，过期后需要重新获取并更新配置
2. 请确保网络连接正常
3. 定时任务会持续运行，按 Ctrl+C 停止
4. 数据文件会持续累积，建议定期清理

## 故障排查

如果遇到获取数据失败的问题：
1. 检查 cookies 是否过期
2. 检查网络连接
3. 检查项目 ID 是否正确
4. 查看控制台输出的错误信息
