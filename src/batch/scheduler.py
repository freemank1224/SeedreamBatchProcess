"""
任务调度器
负责执行批处理任务，管理并发执行和错误处理
"""
import asyncio
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional, Callable
from pathlib import Path

from .core import BatchTask, TaskStatus, TaskType, task_queue, progress_tracker
from ..api.client import api_client
from ..utils.file_handler import file_processor
from ..utils.config import config_manager


class TaskExecutor:
    """任务执行器"""
    
    def __init__(self):
        """初始化任务执行器"""
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
    
    def execute_task(self, task: BatchTask) -> Dict[str, Any]:
        """
        执行单个任务
        
        Args:
            task: 批处理任务
            
        Returns:
            执行结果
        """
        try:
            self.logger.info(f"开始执行任务: {task.id} ({task.task_type.value})")
            
            # 根据任务类型执行不同的操作
            if task.task_type == TaskType.TEXT_TO_IMAGE:
                return self._execute_text_to_image(task)
            elif task.task_type == TaskType.IMAGE_TO_IMAGE:
                return self._execute_image_to_image(task)
            elif task.task_type == TaskType.IMAGE_EDIT:
                return self._execute_image_edit(task)
            elif task.task_type == TaskType.VIDEO_GENERATION:
                return self._execute_video_generation(task)
            else:
                raise ValueError(f"不支持的任务类型: {task.task_type}")
                
        except Exception as e:
            self.logger.error(f"任务执行失败: {task.id}, 错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task.id
            }
    
    def _execute_text_to_image(self, task: BatchTask) -> Dict[str, Any]:
        """执行文生图任务"""
        # 准备参数
        params = {
            "prompt": task.prompt,
            "size": task.parameters.get("size", "2K"),
            "num_images": task.parameters.get("num_images", 1),
            "watermark": task.parameters.get("watermark", True),
            **{k: v for k, v in task.parameters.items() 
               if k not in ["size", "num_images", "watermark"]}
        }
        
        # 调用API
        result = api_client.text_to_image(**params)
        
        if result.get("success"):
            # 下载生成的图像
            downloaded_files = self._download_generated_images(
                result["images"], task.output_dir, task.prompt
            )
            
            result["downloaded_files"] = downloaded_files
            task.output_files = downloaded_files
        
        return result
    
    def _execute_image_to_image(self, task: BatchTask) -> Dict[str, Any]:
        """执行图生图任务"""
        # 准备参数
        params = {
            "prompt": task.prompt,
            "image_paths": task.input_files,
            "image_urls": task.input_urls,
            "size": task.parameters.get("size", "2K"),
            "num_images": task.parameters.get("num_images", 1),
            "watermark": task.parameters.get("watermark", True),
            "mode": task.parameters.get("mode", "edit"),
            **{k: v for k, v in task.parameters.items() 
               if k not in ["size", "num_images", "watermark", "mode"]}
        }
        
        # 调用API
        result = api_client.image_to_image(**params)
        
        if result.get("success"):
            # 下载生成的图像
            downloaded_files = self._download_generated_images(
                result["images"], task.output_dir, task.prompt
            )
            
            result["downloaded_files"] = downloaded_files
            task.output_files = downloaded_files
        
        return result
    
    def _execute_image_edit(self, task: BatchTask) -> Dict[str, Any]:
        """执行图像编辑任务"""
        # 图像编辑实际上也是图生图的一种模式
        task.parameters["mode"] = "edit"
        return self._execute_image_to_image(task)
    
    def _execute_video_generation(self, task: BatchTask) -> Dict[str, Any]:
        """执行视频生成任务"""
        # 准备参数
        params = {
            "prompt": task.prompt,
            "image_paths": task.input_files,
            "image_urls": task.input_urls,
            **task.parameters
        }
        
        # 调用API
        result = api_client.video_generation(**params)
        
        # 注意：视频生成功能暂未实现
        return result
    
    def _download_generated_images(
        self,
        images: list,
        output_dir: str,
        prompt_hint: str = ""
    ) -> list:
        """
        下载生成的图像
        
        Args:
            images: 图像信息列表
            output_dir: 输出目录
            prompt_hint: 提示词提示（用于文件命名）
            
        Returns:
            下载的文件路径列表
        """
        downloaded_files = []
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        for i, image_info in enumerate(images):
            try:
                url = image_info.get("url")
                if not url:
                    continue
                
                # 生成文件名
                prompt_prefix = self._sanitize_filename(prompt_hint[:30]) if prompt_hint else "generated"
                filename = file_processor.generate_filename(
                    prefix=prompt_prefix,
                    suffix=f"_{i+1}" if len(images) > 1 else "",
                    extension=".png",
                    include_timestamp=True
                )
                
                # 确保文件名唯一
                filename = file_processor.create_unique_filename(
                    output_path, filename.rsplit('.', 1)[0], '.png'
                )
                
                file_path = output_path / filename
                
                # 下载图像
                if file_processor.download_image_from_url(url, file_path):
                    downloaded_files.append(str(file_path))
                    self.logger.info(f"图像下载成功: {file_path}")
                else:
                    self.logger.error(f"图像下载失败: {url}")
                    
            except Exception as e:
                self.logger.error(f"处理图像下载时出错: {e}")
        
        return downloaded_files
    
    def _sanitize_filename(self, text: str) -> str:
        """清理文件名中的非法字符"""
        import re
        # 移除或替换非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', text)
        sanitized = re.sub(r'\s+', '_', sanitized)
        return sanitized.strip('_')


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        """初始化任务调度器"""
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.executor = TaskExecutor()
        
        # 并发设置
        self.max_concurrent_tasks = self.config.get("batch.max_concurrent_tasks", 5)
        self.auto_retry = self.config.get("batch.auto_retry", True)
        self.retry_delay = self.config.get("batch.retry_delay", 5)
        
        # 运行状态
        self.is_running = False
        self.should_stop = False
        self._scheduler_thread: Optional[threading.Thread] = None
        
        # 状态回调
        self.status_callbacks: list = []
    
    def add_status_callback(self, callback: Callable[[str, Dict[str, Any]], None]) -> None:
        """添加状态回调函数"""
        self.status_callbacks.append(callback)
    
    def _notify_status(self, event: str, data: Dict[str, Any]) -> None:
        """通知状态变化"""
        for callback in self.status_callbacks:
            try:
                callback(event, data)
            except Exception as e:
                self.logger.error(f"状态回调执行失败: {e}")
    
    def start(self) -> None:
        """启动调度器"""
        if self.is_running:
            self.logger.warning("调度器已在运行中")
            return
        
        self.is_running = True
        self.should_stop = False
        
        # 启动调度线程
        self._scheduler_thread = threading.Thread(
            target=self._scheduler_loop,
            name="TaskScheduler",
            daemon=True
        )
        self._scheduler_thread.start()
        
        self.logger.info("任务调度器已启动")
        self._notify_status("scheduler_started", {})
    
    def stop(self) -> None:
        """停止调度器"""
        if not self.is_running:
            return
        
        self.should_stop = True
        
        # 等待调度线程结束
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._scheduler_thread.join(timeout=10)
        
        self.is_running = False
        self.logger.info("任务调度器已停止")
        self._notify_status("scheduler_stopped", {})
    
    def _scheduler_loop(self) -> None:
        """调度器主循环"""
        with ThreadPoolExecutor(max_workers=self.max_concurrent_tasks) as executor:
            futures = {}
            
            while not self.should_stop:
                try:
                    # 检查是否有任务可以执行
                    while len(futures) < self.max_concurrent_tasks and not self.should_stop:
                        task = task_queue.get_next_task()
                        if not task:
                            break
                        
                        # 提交任务执行
                        future = executor.submit(self._execute_task_with_retry, task)
                        futures[future] = task
                        
                        self.logger.info(f"任务已提交执行: {task.id}")
                    
                    # 检查完成的任务
                    if futures:
                        # 使用短超时来避免阻塞
                        completed_futures = []
                        for future in as_completed(futures, timeout=1):
                            completed_futures.append(future)
                        
                        for future in completed_futures:
                            task = futures.pop(future)
                            try:
                                result = future.result()
                                self._handle_task_completion(task, result)
                            except Exception as e:
                                self.logger.error(f"任务执行异常: {task.id}, 错误: {e}")
                                self._handle_task_failure(task, str(e))
                    
                    # 更新进度
                    self._update_progress()
                    
                    # 短暂休眠避免忙等待
                    time.sleep(0.1)
                    
                except Exception as e:
                    self.logger.error(f"调度器循环异常: {e}")
                    time.sleep(1)
            
            # 等待所有正在执行的任务完成
            for future in futures:
                try:
                    future.result(timeout=30)
                except Exception as e:
                    self.logger.error(f"等待任务完成时出错: {e}")
    
    def _execute_task_with_retry(self, task: BatchTask) -> Dict[str, Any]:
        """执行任务（包含重试逻辑）"""
        max_retries = task.max_retries if self.auto_retry else 0
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(f"重试任务: {task.id}, 第 {attempt} 次重试")
                    time.sleep(self.retry_delay)
                
                result = self.executor.execute_task(task)
                
                if result.get("success"):
                    return result
                else:
                    # 如果这是最后一次尝试，直接返回失败结果
                    if attempt == max_retries:
                        return result
                    
                    # 否则记录错误并继续重试
                    error = result.get("error", "未知错误")
                    self.logger.warning(f"任务执行失败，将重试: {task.id}, 错误: {error}")
                    task.retry_count = attempt + 1
                    
            except Exception as e:
                if attempt == max_retries:
                    return {
                        "success": False,
                        "error": str(e),
                        "task_id": task.id
                    }
                
                self.logger.warning(f"任务执行异常，将重试: {task.id}, 错误: {e}")
                task.retry_count = attempt + 1
        
        return {
            "success": False,
            "error": "重试次数已达上限",
            "task_id": task.id
        }
    
    def _handle_task_completion(self, task: BatchTask, result: Dict[str, Any]) -> None:
        """处理任务完成"""
        if result.get("success"):
            task_queue.update_task_status(
                task.id, 
                TaskStatus.COMPLETED,
                result=result
            )
            self.logger.info(f"任务完成: {task.id}")
            self._notify_status("task_completed", {"task": task, "result": result})
        else:
            self._handle_task_failure(task, result.get("error", "未知错误"))
    
    def _handle_task_failure(self, task: BatchTask, error: str) -> None:
        """处理任务失败"""
        task_queue.update_task_status(
            task.id,
            TaskStatus.FAILED,
            error_message=error
        )
        self.logger.error(f"任务失败: {task.id}, 错误: {error}")
        self._notify_status("task_failed", {"task": task, "error": error})
    
    def _update_progress(self) -> None:
        """更新进度"""
        progress_data = progress_tracker.calculate_progress(task_queue)
        progress_tracker.update_progress(progress_data)
    
    def pause(self) -> None:
        """暂停调度器"""
        # 这里可以实现暂停逻辑
        # 目前简单实现为停止
        self.stop()
    
    def resume(self) -> None:
        """恢复调度器"""
        # 如果已停止，重新启动
        if not self.is_running:
            self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """获取调度器状态"""
        return {
            "is_running": self.is_running,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "auto_retry": self.auto_retry,
            "retry_delay": self.retry_delay,
            "queue_status": task_queue.get_queue_status(),
            "progress": progress_tracker.calculate_progress(task_queue)
        }


# 全局任务调度器实例
task_scheduler = TaskScheduler()