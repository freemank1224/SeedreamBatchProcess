"""
批处理核心模块
负责任务生成、队列管理、调度执行和进度追踪
"""
import asyncio
import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable, Union
from enum import Enum
from dataclasses import dataclass, field
from pathlib import Path
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

from ..api.client import api_client
from ..utils.file_handler import file_processor, directory_scanner, prompt_parser
from ..utils.config import config_manager


class TaskType(Enum):
    """任务类型"""
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"
    IMAGE_EDIT = "image_edit"
    VIDEO_GENERATION = "video_generation"


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"      # 等待中
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


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
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: str = ""
    result: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "prompt": self.prompt,
            "input_files": self.input_files,
            "input_urls": self.input_urls,
            "output_dir": self.output_dir,
            "output_files": self.output_files,
            "parameters": self.parameters,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "result": self.result,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchTask':
        """从字典创建任务"""
        task = cls(
            id=data.get("id", str(uuid.uuid4())),
            task_type=TaskType(data.get("task_type", TaskType.TEXT_TO_IMAGE.value)),
            status=TaskStatus(data.get("status", TaskStatus.PENDING.value)),
            prompt=data.get("prompt", ""),
            input_files=data.get("input_files", []),
            input_urls=data.get("input_urls", []),
            output_dir=data.get("output_dir", ""),
            output_files=data.get("output_files", []),
            parameters=data.get("parameters", {}),
            error_message=data.get("error_message", ""),
            result=data.get("result", {}),
            retry_count=data.get("retry_count", 0),
            max_retries=data.get("max_retries", 3)
        )
        
        # 处理时间字段
        if data.get("created_at"):
            task.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("started_at"):
            task.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(data["completed_at"])
        
        return task


class TaskGenerator:
    """任务生成器"""
    
    def __init__(self):
        """初始化任务生成器"""
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
    
    def generate_text_to_image_tasks(
        self,
        prompts: List[str],
        output_dir: str,
        parameters: Dict[str, Any] = None
    ) -> List[BatchTask]:
        """
        生成文生图任务
        
        Args:
            prompts: 提示词列表
            output_dir: 输出目录
            parameters: 生成参数
            
        Returns:
            任务列表
        """
        tasks = []
        parameters = parameters or {}
        
        for i, prompt in enumerate(prompts):
            task = BatchTask(
                task_type=TaskType.TEXT_TO_IMAGE,
                prompt=prompt,
                output_dir=output_dir,
                parameters=parameters.copy()
            )
            tasks.append(task)
        
        self.logger.info(f"生成 {len(tasks)} 个文生图任务")
        return tasks
    
    def generate_image_to_image_tasks(
        self,
        input_files: List[str],
        prompts: List[str],
        output_dir: str,
        parameters: Dict[str, Any] = None
    ) -> List[BatchTask]:
        """
        生成图生图任务
        
        Args:
            input_files: 输入图像文件列表
            prompts: 提示词列表
            output_dir: 输出目录
            parameters: 生成参数
            
        Returns:
            任务列表
        """
        tasks = []
        parameters = parameters or {}
        
        # 如果提示词只有一个，则对所有图像使用同一个提示词
        if len(prompts) == 1:
            prompt = prompts[0]
            for file_path in input_files:
                task = BatchTask(
                    task_type=TaskType.IMAGE_TO_IMAGE,
                    prompt=prompt,
                    input_files=[file_path],
                    output_dir=output_dir,
                    parameters=parameters.copy()
                )
                tasks.append(task)
        else:
            # 每个文件对应一个提示词
            for file_path, prompt in zip(input_files, prompts):
                task = BatchTask(
                    task_type=TaskType.IMAGE_TO_IMAGE,
                    prompt=prompt,
                    input_files=[file_path],
                    output_dir=output_dir,
                    parameters=parameters.copy()
                )
                tasks.append(task)
        
        self.logger.info(f"生成 {len(tasks)} 个图生图任务")
        return tasks
    
    def generate_batch_tasks_from_directory(
        self,
        input_dir: str,
        prompt: str,
        output_dir: str,
        task_type: TaskType = TaskType.IMAGE_TO_IMAGE,
        parameters: Dict[str, Any] = None
    ) -> List[BatchTask]:
        """
        从目录生成批处理任务
        
        Args:
            input_dir: 输入目录
            prompt: 提示词
            output_dir: 输出目录
            task_type: 任务类型
            parameters: 生成参数
            
        Returns:
            任务列表
        """
        # 扫描目录
        scan_result = directory_scanner.scan_directory(input_dir)
        
        if "error" in scan_result:
            self.logger.error(f"目录扫描失败: {scan_result['error']}")
            return []
        
        # 获取有效图像文件
        valid_files = [
            file_info["path"] 
            for file_info in scan_result["files"] 
            if file_info.get("valid", False)
        ]
        
        if not valid_files:
            self.logger.warning(f"目录中没有找到有效的图像文件: {input_dir}")
            return []
        
        # 生成任务
        if task_type == TaskType.IMAGE_TO_IMAGE:
            return self.generate_image_to_image_tasks(
                valid_files, [prompt], output_dir, parameters
            )
        else:
            self.logger.error(f"不支持的任务类型: {task_type}")
            return []
    
    def generate_tasks_from_prompt_file(
        self,
        prompt_file: str,
        output_dir: str,
        task_type: TaskType = TaskType.TEXT_TO_IMAGE,
        parameters: Dict[str, Any] = None
    ) -> List[BatchTask]:
        """
        从提示词文件生成任务
        
        Args:
            prompt_file: 提示词文件路径
            output_dir: 输出目录
            task_type: 任务类型
            parameters: 生成参数
            
        Returns:
            任务列表
        """
        # 解析提示词文件
        prompts = prompt_parser.parse_prompt_file(prompt_file)
        
        if not prompts:
            self.logger.warning(f"提示词文件中没有找到有效的提示词: {prompt_file}")
            return []
        
        # 生成任务
        if task_type == TaskType.TEXT_TO_IMAGE:
            return self.generate_text_to_image_tasks(prompts, output_dir, parameters)
        else:
            self.logger.error(f"不支持的任务类型: {task_type}")
            return []


class TaskQueue:
    """任务队列"""
    
    def __init__(self):
        """初始化任务队列"""
        self.tasks: Dict[str, BatchTask] = {}
        self.pending_queue: List[str] = []
        self.running_queue: List[str] = []
        self.completed_queue: List[str] = []
        self.failed_queue: List[str] = []
        self._lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
    
    def add_task(self, task: BatchTask) -> None:
        """添加任务"""
        with self._lock:
            self.tasks[task.id] = task
            if task.status == TaskStatus.PENDING:
                self.pending_queue.append(task.id)
            
        self.logger.debug(f"添加任务: {task.id}")
    
    def add_tasks(self, tasks: List[BatchTask]) -> None:
        """批量添加任务"""
        for task in tasks:
            self.add_task(task)
        
        self.logger.info(f"批量添加 {len(tasks)} 个任务")
    
    def get_next_task(self) -> Optional[BatchTask]:
        """获取下一个待执行任务"""
        with self._lock:
            if self.pending_queue:
                task_id = self.pending_queue.pop(0)
                task = self.tasks[task_id]
                task.status = TaskStatus.RUNNING
                task.started_at = datetime.now()
                self.running_queue.append(task_id)
                return task
        
        return None
    
    def update_task_status(self, task_id: str, status: TaskStatus, **kwargs) -> None:
        """更新任务状态"""
        with self._lock:
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            old_status = task.status
            task.status = status
            
            # 更新其他属性
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            
            # 更新队列
            self._move_task_between_queues(task_id, old_status, status)
            
            # 设置完成时间
            if status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                task.completed_at = datetime.now()
    
    def _move_task_between_queues(self, task_id: str, old_status: TaskStatus, new_status: TaskStatus) -> None:
        """在队列间移动任务"""
        # 从旧队列移除
        if old_status == TaskStatus.PENDING and task_id in self.pending_queue:
            self.pending_queue.remove(task_id)
        elif old_status == TaskStatus.RUNNING and task_id in self.running_queue:
            self.running_queue.remove(task_id)
        elif old_status == TaskStatus.COMPLETED and task_id in self.completed_queue:
            self.completed_queue.remove(task_id)
        elif old_status == TaskStatus.FAILED and task_id in self.failed_queue:
            self.failed_queue.remove(task_id)
        
        # 添加到新队列
        if new_status == TaskStatus.PENDING:
            self.pending_queue.append(task_id)
        elif new_status == TaskStatus.RUNNING:
            self.running_queue.append(task_id)
        elif new_status == TaskStatus.COMPLETED:
            self.completed_queue.append(task_id)
        elif new_status == TaskStatus.FAILED:
            self.failed_queue.append(task_id)
    
    def get_task(self, task_id: str) -> Optional[BatchTask]:
        """获取任务"""
        return self.tasks.get(task_id)
    
    def get_tasks_by_status(self, status: TaskStatus) -> List[BatchTask]:
        """按状态获取任务"""
        return [
            task for task in self.tasks.values()
            if task.status == status
        ]
    
    def get_queue_status(self) -> Dict[str, int]:
        """获取队列状态"""
        with self._lock:
            return {
                "pending": len(self.pending_queue),
                "running": len(self.running_queue),
                "completed": len(self.completed_queue),
                "failed": len(self.failed_queue),
                "total": len(self.tasks)
            }
    
    def clear_completed_tasks(self) -> int:
        """清理已完成的任务"""
        with self._lock:
            completed_ids = self.completed_queue.copy()
            for task_id in completed_ids:
                del self.tasks[task_id]
            self.completed_queue.clear()
            
        self.logger.info(f"清理 {len(completed_ids)} 个已完成任务")
        return len(completed_ids)
    
    def save_to_file(self, file_path: str) -> None:
        """保存队列到文件"""
        try:
            queue_data = {
                "tasks": {task_id: task.to_dict() for task_id, task in self.tasks.items()},
                "pending_queue": self.pending_queue,
                "running_queue": self.running_queue,
                "completed_queue": self.completed_queue,
                "failed_queue": self.failed_queue,
                "saved_at": datetime.now().isoformat()
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(queue_data, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"任务队列已保存到: {file_path}")
            
        except Exception as e:
            self.logger.error(f"保存任务队列失败: {e}")
    
    def load_from_file(self, file_path: str) -> None:
        """从文件加载队列"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                queue_data = json.load(f)
            
            # 重建任务
            self.tasks = {
                task_id: BatchTask.from_dict(task_data)
                for task_id, task_data in queue_data.get("tasks", {}).items()
            }
            
            # 重建队列
            self.pending_queue = queue_data.get("pending_queue", [])
            self.running_queue = queue_data.get("running_queue", [])
            self.completed_queue = queue_data.get("completed_queue", [])
            self.failed_queue = queue_data.get("failed_queue", [])
            
            self.logger.info(f"任务队列已从文件加载: {file_path}")
            
        except Exception as e:
            self.logger.error(f"加载任务队列失败: {e}")


class ProgressTracker:
    """进度追踪器"""
    
    def __init__(self):
        """初始化进度追踪器"""
        self.progress_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.logger = logging.getLogger(__name__)
        
    def add_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """添加进度回调函数"""
        self.progress_callbacks.append(callback)
    
    def update_progress(self, progress_data: Dict[str, Any]) -> None:
        """更新进度"""
        for callback in self.progress_callbacks:
            try:
                callback(progress_data)
            except Exception as e:
                self.logger.error(f"进度回调函数执行失败: {e}")
    
    def calculate_progress(self, queue: TaskQueue) -> Dict[str, Any]:
        """计算总体进度"""
        status = queue.get_queue_status()
        total = status["total"]
        
        if total == 0:
            return {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "running_tasks": 0,
                "pending_tasks": 0,
                "progress_percentage": 0.0,
                "status": "idle"
            }
        
        completed = status["completed"]
        failed = status["failed"]
        running = status["running"]
        pending = status["pending"]
        
        # 计算进度百分比
        progress_percentage = (completed + failed) / total * 100
        
        # 确定整体状态
        if running > 0:
            overall_status = "running"
        elif pending > 0:
            overall_status = "pending"
        elif failed > 0 and completed == 0:
            overall_status = "failed"
        elif completed > 0:
            overall_status = "completed"
        else:
            overall_status = "idle"
        
        return {
            "total_tasks": total,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "running_tasks": running,
            "pending_tasks": pending,
            "progress_percentage": progress_percentage,
            "status": overall_status,
            "success_rate": completed / (completed + failed) * 100 if (completed + failed) > 0 else 0
        }


# 全局实例
task_generator = TaskGenerator()
task_queue = TaskQueue()
progress_tracker = ProgressTracker()