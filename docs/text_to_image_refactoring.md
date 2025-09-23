# 文生图功能重构设计文档

## 1. 背景说明

当前的批处理设计对于"文生图"功能的区分不够明确，需要针对"文生单图"和"文生组图"两种模式进行重构，并清晰分离单次任务和批处理任务。

## 2. 重构目标

1. 优化用户界面，使功能区分更加明确
2. 增强批处理核心功能，支持不同类型的文生图任务
3. 改进文件处理和命名逻辑
4. 实现多层次进度跟踪系统

## 3. 重构任务列表

### 3.1 改进文生图UI界面结构

- 在"文生图"标签页顶部添加明显的切换按钮，区分"文生单图"和"文生组图"两种模式
- 为切换按钮添加清晰的说明文字，解释其作用
- 明确分离单次任务和批处理任务区域，避免混淆
- 根据所选模式动态调整界面组件和提示信息

### 3.2 增强批处理核心功能

- 扩展`BatchTask`类，添加对"文生单图"和"文生组图"模式的支持
- 在任务配置中添加序列图像生成相关参数：
  - `sequential_image_generation`参数
  - `sequential_image_generation_options`参数
- 更新任务生成器，支持处理多种格式的提示词文件(txt, csv, xlsx)
- 实现针对不同模式的任务调度逻辑

### 3.3 优化文件处理功能

- 改进提示词解析器，支持多种文件格式的正确解析
- 为"文生组图"模式添加提示词格式验证和示例提示
- 实现生成图像的智能命名系统：
  - 文生单图：根据提示词顺序编号
  - 文生组图：同时反映提示词顺序和组内相对顺序

### 3.4 实现多层次进度跟踪系统

- 设计分层级的进度显示机制：
  - 普通批处理任务：显示总体进度（如：已完成5/20张，25%）
  - 组图生成任务：显示当前组图的生成进度（如：当前组图2/4张，50%）
  - 组图批处理任务：同时显示总体批处理进度和当前组图进度
- 实现进度条和文字说明相结合的显示方式
- 添加实时更新生成图片的功能

## 4. 实现细节

### 4.1 UI结构改进

```python
# 在文生图标签页顶部添加模式切换按钮
with gr.Tab("📝 文生图", id="text_to_image"):
    with gr.Row():
        gr.Markdown("### 请选择文生图模式")
        generation_mode = gr.Radio(
            choices=[("文生单图", "single"), ("文生组图", "series")],
            label="生成模式",
            value="single",
            info="文生单图：生成独立的单张图片 | 文生组图：生成一组相关联的图片序列"
        )
    
    # 根据模式显示不同的说明
    single_mode_info = gr.Markdown(
        "#### 文生单图模式\n单张图片生成，每个提示词对应一张图片。",
        visible=True
    )
    series_mode_info = gr.Markdown(
        "#### 文生组图模式\n生成一组相关联的图片序列，适合制作分镜、展示变化过程等。",
        visible=False
    )
    
    # 后续分别创建单次任务和批处理任务区域
```

### 4.2 批处理核心功能扩展

```python
@dataclass
class BatchTask:
    """批处理任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_type: TaskType = TaskType.TEXT_TO_IMAGE
    status: TaskStatus = TaskStatus.PENDING
    prompt: str = ""
    input_files: List[str] = field(default_factory=list)
    input_urls: List[str] = field(default_factory=list)
    output_dir: str = ""
    output_files: List[str] = field(default_factory=list)
    # 新增字段
    is_sequential: bool = False  # 是否为组图生成模式
    max_images: int = 1  # 组图模式下的图片数量
    current_subtask: int = 0  # 当前处理的子任务索引
    total_subtasks: int = 1  # 总子任务数量
```

### 4.3 文件处理功能优化

```python
def parse_prompts_file(file_path: str, mode: str = "single") -> List[str]:
    """解析提示词文件
    
    Args:
        file_path: 文件路径
        mode: 生成模式，'single'为文生单图，'series'为文生组图
    
    Returns:
        提示词列表
    """
    ext = Path(file_path).suffix.lower()
    prompts = []
    
    if ext == '.txt':
        with open(file_path, 'r', encoding='utf-8') as f:
            prompts = [line.strip() for line in f if line.strip()]
    elif ext == '.csv':
        import csv
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            prompts = [row[0] for row in reader if row and row[0].strip()]
    elif ext == '.xlsx':
        import pandas as pd
        df = pd.read_excel(file_path, header=None)
        prompts = [str(p).strip() for p in df[0].tolist() if str(p).strip()]
    
    # 组图模式下验证提示词格式
    if mode == "series":
        for i, prompt in enumerate(prompts):
            if "生成" not in prompt and "系列" not in prompt and "组" not in prompt:
                logging.warning(f"组图模式下的提示词 #{i+1} 可能格式不正确: {prompt}")
    
    return prompts
```

### 4.4 多层次进度跟踪系统

```python
@dataclass
class ProgressData:
    """进度数据"""
    total_tasks: int = 0
    completed_tasks: int = 0
    current_task_index: int = 0
    current_task_id: str = ""
    current_task_prompt: str = ""
    is_sequential: bool = False
    total_images_in_sequence: int = 0
    completed_images_in_sequence: int = 0
    status: str = "idle"
    
    @property
    def total_progress_percentage(self) -> float:
        """计算总体进度百分比"""
        return (self.completed_tasks / max(1, self.total_tasks)) * 100 if self.total_tasks > 0 else 0
    
    @property
    def sequence_progress_percentage(self) -> float:
        """计算当前序列进度百分比"""
        return (self.completed_images_in_sequence / max(1, self.total_images_in_sequence)) * 100 if self.is_sequential else 0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "total_progress_percentage": self.total_progress_percentage,
            "current_task_index": self.current_task_index,
            "current_task_id": self.current_task_id,
            "current_task_prompt": self.current_task_prompt,
            "is_sequential": self.is_sequential,
            "total_images_in_sequence": self.total_images_in_sequence,
            "completed_images_in_sequence": self.completed_images_in_sequence,
            "sequence_progress_percentage": self.sequence_progress_percentage,
            "status": self.status
        }
```

## 5. 用户界面优化示例

### 5.1 文生单图模式

单次任务区域：
- 提示词输入框
- 图像尺寸选择
- 生成按钮
- 结果显示区域

批处理任务区域：
- 提示词文件上传
- 批量提示词输入
- 输出目录设置
- 批量生成按钮
- 进度显示

### 5.2 文生组图模式

单次任务区域：
- 提示词输入框（带有格式提示）
- 图像尺寸选择
- 组图数量设置
- 生成按钮
- 结果显示区域

批处理任务区域：
- 提示词文件上传（带有格式说明）
- 批量提示词输入（带有格式提示）
- 输出目录设置
- 批量生成按钮
- 多层次进度显示

## 6. 实施计划

1. 先修改UI界面结构，添加模式切换功能
2. 更新批处理核心功能，支持两种模式
3. 改进文件处理和命名逻辑
4. 实现多层次进度跟踪系统
5. 进行功能测试和优化