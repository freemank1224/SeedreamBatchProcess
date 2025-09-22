# 🎨 Seedream 批处理应用

基于 Seedream API 的图像批处理工具，支持文生图、图生图、图像编辑等功能，具备强大的批处理能力。

## ✨ 主要特性

- **🖼️ 多种生成模式**: 支持文生图、图生图、图像编辑
- **⚡ 批处理能力**: 支持大量任务的自动化批处理
- **📊 进度监控**: 实时显示任务进度和状态
- **🛡️ 安全可靠**: API密钥安全管理，错误处理机制完善
- **🎯 用户友好**: 基于Gradio的直观Web界面
- **🔧 灵活配置**: 丰富的参数配置和自定义选项

## 🚀 快速开始

### 环境要求

- Python 3.8 或更高版本
- Windows、macOS 或 Linux 系统
- 有效的 ARK API Key

### 一键启动

#### Windows 用户
```bash
# 双击运行或在命令行执行
start.bat
```

#### Linux/macOS 用户
```bash
# 添加执行权限
chmod +x start.sh

# 运行启动脚本
./start.sh
```

#### 手动启动
```bash
# 克隆项目
git clone <repository-url>
cd SeedreamBatchProcess

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境（Windows）
venv\Scripts\activate
# 或者（Linux/macOS）
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动应用
python main.py
```

### 配置API密钥

1. 启动应用后，在Web界面中找到"系统配置"面板
2. 输入您的 ARK API Key
3. 点击"保存密钥"按钮
4. 点击"测试连接"验证API可用性

## 📖 使用指南

### 文生图功能

1. 在"文生图"标签页输入提示词
2. 选择图像尺寸和生成数量
3. 点击"生成图像"开始生成

**批量生成**:
- 可以输入多行提示词（每行一个）
- 或上传提示词文件（支持 .txt 和 .csv 格式）
- 设置输出目录后点击"批量生成"

### 图生图功能

1. 上传图像文件或指定图像目录
2. 输入编辑指令描述想要的修改
3. 选择处理模式：
   - **图像编辑**: 对输入图像进行修改
   - **组图生成**: 基于输入图像生成一系列相关图像
4. 点击"处理图像"开始处理

### 批处理管理

在"批处理管理"标签页可以：
- **开始/暂停/停止** 批处理队列
- **查看任务状态** 和进度
- **管理任务队列**（清理、保存、加载）

### 进度监控

在"进度监控"标签页可以：
- 查看**实时进度**和任务统计
- 监控**系统日志**
- 查看**任务状态分布**

## 📁 项目结构

```
SeedreamBatchProcess/
├── src/                    # 源码目录
│   ├── api/               # API通信模块
│   ├── batch/             # 批处理核心模块
│   ├── ui/                # 用户界面模块
│   └── utils/             # 工具模块
├── config/                # 配置文件目录
├── input/                 # 输入文件目录
├── output/                # 输出文件目录
├── logs/                  # 日志文件目录
├── scripts/               # 启动脚本目录
├── docs/                  # 文档目录
├── main.py                # 主程序入口
├── requirements.txt       # Python依赖
├── start.bat              # Windows启动脚本
└── start.sh               # Linux/macOS启动脚本
```

## ⚙️ 配置说明

### 默认配置

应用会自动创建默认配置文件 `config/default_config.yaml`，包含：

- **API设置**: 服务地址、模型、超时等
- **批处理设置**: 并发数量、重试策略等
- **图像设置**: 支持格式、大小限制等
- **界面设置**: 主题、端口等

### 自定义配置

可以创建 `config/config.yaml` 文件来覆盖默认设置：

```yaml
api:
  base_url: "https://ark.cn-beijing.volces.com/api/v3"
  model: "doubao-seedream-4-0-250828"
  timeout: 30

batch:
  max_concurrent_tasks: 5
  auto_retry: true
  retry_delay: 5

image:
  max_size_mb: 10
  default_size: "2K"
```

## 🛠️ 技术架构

- **前后端框架**: Gradio
- **API客户端**: OpenAI Python SDK
- **图像处理**: Pillow (PIL)
- **配置管理**: PyYAML
- **日志系统**: Python logging
- **并发处理**: ThreadPoolExecutor

## 📄 API支持

基于 Seedream API，支持：

- **文生图**: 根据文本描述生成图像
- **图生图**: 基于输入图像和文本指令生成新图像
- **图像编辑**: 对图像进行局部或整体修改
- **组图生成**: 生成一系列相关或连贯的图像

## 🔒 安全特性

- **API密钥保护**: 密钥加密存储，不会在日志中泄露
- **输入验证**: 严格的文件格式和大小验证
- **错误处理**: 完善的异常处理和重试机制
- **资源管理**: 自动清理临时文件和缓存

## 🐛 故障排除

### 常见问题

1. **API连接失败**
   - 检查网络连接
   - 验证API密钥是否正确
   - 确认API服务地址是否可访问

2. **图像处理失败**
   - 检查图像文件格式是否支持
   - 确认文件大小是否超过限制
   - 查看日志文件获取详细错误信息

3. **批处理停止**
   - 检查磁盘空间是否充足
   - 查看API配额是否耗尽
   - 检查网络连接稳定性

### 日志查看

日志文件位于 `logs/` 目录下：
- `seedream_app.log`: 应用主日志
- 可在"进度监控"标签页实时查看日志

## 🤝 贡献指南

欢迎提交问题报告和功能建议！

## 📜 许可证

本项目基于 MIT 许可证开源。

## 📞 支持

如有问题，请查看：
- 项目文档: `docs/` 目录
- 开发进度: `docs/PROGRESS.md`
- 使用指南: `docs/GUIDE.md`

---

**享受创作的乐趣！** 🎨✨

