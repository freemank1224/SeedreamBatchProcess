"""
Gradio用户界面主界面
"""
import gradio as gr
import logging
from typing import Dict, Any, List, Tuple, Optional
from pathlib import Path
import json

from ..batch import (
    TaskType, TaskStatus, task_generator, task_queue, 
    progress_tracker, task_scheduler
)
from ..utils.config import config_manager
from ..utils.file_handler import directory_scanner, prompt_parser
from ..api.client import api_client


class SeedreamUI:
    """Seedream批处理应用主界面"""
    
    def __init__(self):
        """初始化UI"""
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # UI状态
        self.current_progress = {"progress_percentage": 0, "status": "idle"}
        
        # 设置进度回调
        progress_tracker.add_progress_callback(self._update_progress_display)
        task_scheduler.add_status_callback(self._handle_scheduler_event)
    
    def _update_progress_display(self, progress_data: Dict[str, Any]) -> None:
        """更新进度显示"""
        self.current_progress = progress_data
    
    def _handle_scheduler_event(self, event: str, data: Dict[str, Any]) -> None:
        """处理调度器事件"""
        self.logger.info(f"调度器事件: {event}")
    
    def create_interface(self) -> gr.Blocks:
        """创建Gradio界面"""
        with gr.Blocks(
            title="Seedream 批处理应用",
            theme=gr.themes.Soft(),
            css=self._get_custom_css()
        ) as interface:
            
            # 标题和说明
            gr.Markdown("""
            # 🎨 Seedream 批处理应用
            
            基于 Seedream API 的图像批处理工具，支持文生图、图生图、图像编辑等功能。
            """)
            
            # 配置面板
            with gr.Accordion("⚙️ 系统配置", open=False):
                self._create_config_panel()
            
            # 主功能面板
            with gr.Tabs() as main_tabs:
                # 文生图标签页
                with gr.Tab("📝 文生图", id="text_to_image"):
                    self._create_text_to_image_tab()
                
                # 图生图标签页
                with gr.Tab("🖼️ 图生图", id="image_to_image"):
                    self._create_image_to_image_tab()
                
                # 批处理管理标签页
                with gr.Tab("⚡ 批处理管理", id="batch_management"):
                    self._create_batch_management_tab()
                
                # 进度监控标签页
                with gr.Tab("📊 进度监控", id="progress_monitor"):
                    self._create_progress_monitor_tab()
            
            # 底部状态栏
            self._create_status_bar()
        
        return interface
    
    def _create_config_panel(self) -> None:
        """创建配置面板"""
        with gr.Row():
            with gr.Column(scale=1):
                api_key_input = gr.Textbox(
                    label="API 密钥",
                    placeholder="请输入您的 ARK API Key",
                    type="password",
                    value=self.config.get_api_key() or ""
                )
                
                with gr.Row():
                    save_api_key_btn = gr.Button("保存密钥", variant="primary", size="sm")
                    test_connection_btn = gr.Button("测试连接", variant="secondary", size="sm")
            
            with gr.Column(scale=1):
                model_info = gr.JSON(
                    label="模型信息",
                    value=api_client.get_model_info()
                )
        
        # 配置事件
        save_api_key_btn.click(
            fn=self._save_api_key,
            inputs=[api_key_input],
            outputs=[gr.Textbox(label="保存结果", visible=False)]
        )
        
        test_connection_btn.click(
            fn=self._test_api_connection,
            outputs=[gr.Textbox(label="连接测试结果", visible=False)]
        )
    
    def _create_text_to_image_tab(self) -> None:
        """创建文生图标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                # 单个提示词输入
                with gr.Group():
                    gr.Markdown("### 单个提示词生成")
                    single_prompt = gr.Textbox(
                        label="提示词",
                        placeholder="输入图像描述...",
                        lines=3
                    )
                    
                    with gr.Row():
                        single_size = gr.Dropdown(
                            choices=["1K", "2K", "4K"],
                            label="图像尺寸",
                            value="2K"
                        )
                        single_num_images = gr.Slider(
                            minimum=1,
                            maximum=10,
                            step=1,
                            label="生成数量",
                            value=1
                        )
                    
                    single_generate_btn = gr.Button("生成图像", variant="primary")
                
                # 批量提示词输入
                with gr.Group():
                    gr.Markdown("### 批量提示词生成")
                    
                    batch_prompts = gr.Textbox(
                        label="批量提示词（每行一个）",
                        placeholder="提示词1\n提示词2\n提示词3...",
                        lines=5
                    )
                    
                    prompt_file = gr.File(
                        label="或上传提示词文件",
                        file_types=[".txt", ".csv"]
                    )
                    
                    with gr.Row():
                        batch_size = gr.Dropdown(
                            choices=["1K", "2K", "4K"],
                            label="图像尺寸",
                            value="2K"
                        )
                        batch_output_dir = gr.Textbox(
                            label="输出目录",
                            value=str(self.config.get_absolute_path("output"))
                        )
                    
                    batch_generate_btn = gr.Button("批量生成", variant="primary")
            
            with gr.Column(scale=1):
                # 生成结果显示
                result_gallery = gr.Gallery(
                    label="生成结果",
                    show_label=True,
                    elem_id="result_gallery",
                    columns=2,
                    rows=2,
                    height="auto"
                )
                
                result_info = gr.JSON(
                    label="生成信息",
                    visible=False
                )
        
        # 事件绑定
        single_generate_btn.click(
            fn=self._generate_single_image,
            inputs=[single_prompt, single_size, single_num_images],
            outputs=[result_gallery, result_info]
        )
        
        batch_generate_btn.click(
            fn=self._generate_batch_images,
            inputs=[batch_prompts, prompt_file, batch_size, batch_output_dir],
            outputs=[result_info]
        )
    
    def _create_image_to_image_tab(self) -> None:
        """创建图生图标签页"""
        with gr.Row():
            with gr.Column(scale=2):
                # 图像输入
                with gr.Group():
                    gr.Markdown("### 图像输入")
                    input_images = gr.File(
                        label="选择图像文件",
                        file_count="multiple",
                        file_types=["image"]
                    )
                    
                    input_dir = gr.Textbox(
                        label="或输入图像目录路径",
                        placeholder="输入包含图像的目录路径"
                    )
                    
                    scan_dir_btn = gr.Button("扫描目录", size="sm")
                    
                    dir_info = gr.JSON(
                        label="目录扫描结果",
                        visible=False
                    )
                
                # 编辑参数
                with gr.Group():
                    gr.Markdown("### 编辑参数")
                    edit_prompt = gr.Textbox(
                        label="编辑指令",
                        placeholder="描述您想要对图像进行的修改...",
                        lines=3
                    )
                    
                    with gr.Row():
                        edit_mode = gr.Radio(
                            choices=[("图像编辑", "edit"), ("组图生成", "generate")],
                            label="处理模式",
                            value="edit"
                        )
                        
                        edit_size = gr.Dropdown(
                            choices=["1K", "2K", "4K"],
                            label="输出尺寸",
                            value="2K"
                        )
                    
                    edit_output_dir = gr.Textbox(
                        label="输出目录",
                        value=str(self.config.get_absolute_path("output"))
                    )
                    
                    process_images_btn = gr.Button("处理图像", variant="primary")
            
            with gr.Column(scale=1):
                # 处理结果
                processed_gallery = gr.Gallery(
                    label="处理结果",
                    show_label=True,
                    columns=2,
                    rows=2,
                    height="auto"
                )
                
                process_info = gr.JSON(
                    label="处理信息",
                    visible=False
                )
        
        # 事件绑定
        scan_dir_btn.click(
            fn=self._scan_image_directory,
            inputs=[input_dir],
            outputs=[dir_info]
        )
        
        process_images_btn.click(
            fn=self._process_images,
            inputs=[
                input_images, input_dir, edit_prompt, 
                edit_mode, edit_size, edit_output_dir
            ],
            outputs=[processed_gallery, process_info]
        )
    
    def _create_batch_management_tab(self) -> None:
        """创建批处理管理标签页"""
        with gr.Row():
            with gr.Column(scale=1):
                # 队列控制
                with gr.Group():
                    gr.Markdown("### 队列控制")
                    
                    with gr.Row():
                        start_btn = gr.Button("开始处理", variant="primary")
                        pause_btn = gr.Button("暂停", variant="secondary")
                        stop_btn = gr.Button("停止", variant="stop")
                    
                    with gr.Row():
                        clear_completed_btn = gr.Button("清理已完成", size="sm")
                        save_queue_btn = gr.Button("保存队列", size="sm")
                        load_queue_btn = gr.Button("加载队列", size="sm")
                
                # 队列状态
                with gr.Group():
                    gr.Markdown("### 队列状态")
                    queue_status = gr.JSON(
                        label="队列状态",
                        value=task_queue.get_queue_status()
                    )
                    
                    refresh_status_btn = gr.Button("刷新状态", size="sm")
            
            with gr.Column(scale=2):
                # 任务列表
                task_list = gr.Dataframe(
                    headers=["ID", "类型", "状态", "提示词", "创建时间"],
                    datatype=["str", "str", "str", "str", "str"],
                    label="任务列表",
                    height=400,
                    interactive=False
                )
                
                refresh_tasks_btn = gr.Button("刷新任务列表")
        
        # 事件绑定
        start_btn.click(
            fn=self._start_batch_processing,
            outputs=[queue_status]
        )
        
        pause_btn.click(
            fn=self._pause_batch_processing,
            outputs=[queue_status]
        )
        
        stop_btn.click(
            fn=self._stop_batch_processing,
            outputs=[queue_status]
        )
        
        refresh_status_btn.click(
            fn=self._get_queue_status,
            outputs=[queue_status]
        )
        
        refresh_tasks_btn.click(
            fn=self._get_task_list,
            outputs=[task_list]
        )
    
    def _create_progress_monitor_tab(self) -> None:
        """创建进度监控标签页"""
        with gr.Column():
            # 总体进度
            with gr.Group():
                gr.Markdown("### 总体进度")
                
                progress_bar = gr.Progress()
                
                with gr.Row():
                    progress_info = gr.JSON(
                        label="进度详情",
                        value=self.current_progress
                    )
                    
                    progress_chart = gr.BarPlot(
                        title="任务状态分布",
                        x="状态",
                        y="数量",
                        height=300
                    )
            
            # 实时日志
            with gr.Group():
                gr.Markdown("### 实时日志")
                log_display = gr.Textbox(
                    label="系统日志",
                    lines=10,
                    max_lines=20,
                    autoscroll=True,
                    interactive=False
                )
                
                with gr.Row():
                    refresh_log_btn = gr.Button("刷新日志", size="sm")
                    clear_log_btn = gr.Button("清空日志", size="sm")
    
    def _create_status_bar(self) -> None:
        """创建底部状态栏"""
        with gr.Row():
            status_text = gr.Textbox(
                value="系统就绪",
                label="状态",
                interactive=False,
                scale=3
            )
            
            version_info = gr.Textbox(
                value="v1.0.0",
                label="版本",
                interactive=False,
                scale=1
            )
    
    def _get_custom_css(self) -> str:
        """获取自定义CSS样式"""
        return """
        .gradio-container {
            max-width: 1400px !important;
        }
        
        #result_gallery {
            min-height: 400px;
        }
        
        .progress-bar {
            background: linear-gradient(90deg, #4CAF50, #8BC34A);
        }
        """
    
    # UI事件处理方法
    def _save_api_key(self, api_key: str) -> str:
        """保存API密钥"""
        try:
            if api_client.set_api_key(api_key):
                return "API密钥保存成功"
            else:
                return "API密钥保存失败"
        except Exception as e:
            return f"保存失败: {e}"
    
    def _test_api_connection(self) -> str:
        """测试API连接"""
        try:
            if api_client.test_connection():
                return "连接成功"
            else:
                return "连接失败"
        except Exception as e:
            return f"连接测试失败: {e}"
    
    def _generate_single_image(
        self, 
        prompt: str, 
        size: str, 
        num_images: int
    ) -> Tuple[List[str], Dict[str, Any]]:
        """生成单个图像"""
        try:
            if not prompt.strip():
                return [], {"error": "请输入提示词"}
            
            result = api_client.text_to_image(
                prompt=prompt,
                size=size,
                num_images=num_images
            )
            
            if result.get("success"):
                # 这里应该下载图像并返回本地路径
                # 暂时返回URL
                image_urls = [img["url"] for img in result["images"]]
                return image_urls, result
            else:
                return [], result
                
        except Exception as e:
            return [], {"error": str(e)}
    
    def _generate_batch_images(
        self,
        batch_prompts: str,
        prompt_file: Optional[str],
        size: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """批量生成图像"""
        try:
            prompts = []
            
            # 处理文本输入的提示词
            if batch_prompts.strip():
                prompts.extend([
                    line.strip() 
                    for line in batch_prompts.split('\n') 
                    if line.strip()
                ])
            
            # 处理文件输入的提示词
            if prompt_file:
                file_prompts = prompt_parser.parse_prompt_file(prompt_file)
                prompts.extend(file_prompts)
            
            if not prompts:
                return {"error": "请输入提示词或上传提示词文件"}
            
            # 生成任务
            tasks = task_generator.generate_text_to_image_tasks(
                prompts=prompts,
                output_dir=output_dir,
                parameters={"size": size}
            )
            
            # 添加到队列
            task_queue.add_tasks(tasks)
            
            return {
                "success": True,
                "message": f"已添加 {len(tasks)} 个生成任务到队列",
                "task_count": len(tasks)
            }
            
        except Exception as e:
            return {"error": str(e)}
    
    def _scan_image_directory(self, directory: str) -> Dict[str, Any]:
        """扫描图像目录"""
        try:
            if not directory.strip():
                return {"error": "请输入目录路径"}
            
            result = directory_scanner.scan_directory(directory)
            return result
            
        except Exception as e:
            return {"error": str(e)}
    
    def _process_images(
        self,
        input_images: List[str],
        input_dir: str,
        prompt: str,
        mode: str,
        size: str,
        output_dir: str
    ) -> Tuple[List[str], Dict[str, Any]]:
        """处理图像"""
        try:
            if not prompt.strip():
                return [], {"error": "请输入编辑指令"}
            
            # 收集输入文件
            input_files = []
            
            if input_images:
                input_files.extend(input_images)
            
            if input_dir.strip():
                scan_result = directory_scanner.scan_directory(input_dir)
                if "files" in scan_result:
                    valid_files = [
                        file_info["path"] 
                        for file_info in scan_result["files"] 
                        if file_info.get("valid", False)
                    ]
                    input_files.extend(valid_files)
            
            if not input_files:
                return [], {"error": "请选择输入图像"}
            
            # 生成任务
            task_type = TaskType.IMAGE_TO_IMAGE
            tasks = task_generator.generate_image_to_image_tasks(
                input_files=input_files,
                prompts=[prompt],
                output_dir=output_dir,
                parameters={"size": size, "mode": mode}
            )
            
            # 添加到队列
            task_queue.add_tasks(tasks)
            
            return [], {
                "success": True,
                "message": f"已添加 {len(tasks)} 个处理任务到队列",
                "task_count": len(tasks)
            }
            
        except Exception as e:
            return [], {"error": str(e)}
    
    def _start_batch_processing(self) -> Dict[str, Any]:
        """开始批处理"""
        try:
            task_scheduler.start()
            return task_queue.get_queue_status()
        except Exception as e:
            return {"error": str(e)}
    
    def _pause_batch_processing(self) -> Dict[str, Any]:
        """暂停批处理"""
        try:
            task_scheduler.pause()
            return task_queue.get_queue_status()
        except Exception as e:
            return {"error": str(e)}
    
    def _stop_batch_processing(self) -> Dict[str, Any]:
        """停止批处理"""
        try:
            task_scheduler.stop()
            return task_queue.get_queue_status()
        except Exception as e:
            return {"error": str(e)}
    
    def _get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return task_queue.get_queue_status()
    
    def _get_task_list(self) -> List[List[str]]:
        """获取任务列表"""
        try:
            tasks = []
            for task in task_queue.tasks.values():
                tasks.append([
                    task.id[:8],  # 截短ID显示
                    task.task_type.value,
                    task.status.value,
                    task.prompt[:50] + "..." if len(task.prompt) > 50 else task.prompt,
                    task.created_at.strftime("%m-%d %H:%M:%S")
                ])
            return tasks
        except Exception as e:
            return [["错误", str(e), "", "", ""]]


# 全局UI实例
seedream_ui = SeedreamUI()