"""
Seedream API客户端
负责与Seedream服务进行通信，实现文生图、图生图、图像编辑、视频生成等功能
"""
import os
import base64
import asyncio
import logging
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from openai import OpenAI
import requests
from PIL import Image
import io

from ..utils.config import config_manager

logger = logging.getLogger(__name__)


class SeedreamAPIClient:
    """Seedream API客户端"""
    
    def __init__(self):
        """初始化API客户端"""
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 初始化OpenAI客户端
        self._init_client()
    
    def _init_client(self) -> None:
        """初始化OpenAI客户端"""
        api_key = self.config.get_api_key()
        if not api_key:
            logger.warning("API密钥未设置，将在应用启动后设置")
            self.client = None
            return
        
        base_url = self.config.get("api.base_url")
        
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        self.logger.info(f"API客户端初始化完成，服务地址: {base_url}")
    
    def set_api_key(self, api_key: str) -> bool:
        """
        设置API密钥并重新初始化客户端
        
        Args:
            api_key: ARK API密钥
            
        Returns:
            是否设置成功
        """
        try:
            # 保存API密钥到配置
            self.config.set("api.ark_api_key", api_key)
            self.config.save()
            
            # 重新初始化客户端
            self._init_client()
            
            return self.client is not None
        except Exception as e:
            logger.error(f"设置API密钥失败: {e}")
            return False
    
    def _encode_image_to_base64(self, image_path: Union[str, Path]) -> str:
        """
        将图像文件编码为base64字符串
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            base64编码的图像字符串
        """
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            self.logger.error(f"图像编码失败: {e}")
            raise
    
    def _validate_image_urls(self, image_urls: List[str]) -> List[str]:
        """
        验证图像URL的可用性
        
        Args:
            image_urls: 图像URL列表
            
        Returns:
            验证后的URL列表
        """
        valid_urls = []
        for url in image_urls:
            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    valid_urls.append(url)
                else:
                    self.logger.warning(f"图像URL不可访问: {url} (状态码: {response.status_code})")
            except Exception as e:
                self.logger.warning(f"验证图像URL失败: {url}, 错误: {e}")
        
        return valid_urls
    
    def text_to_image(
        self,
        prompt: str,
        size: str = "2K",
        num_images: int = 1,
        watermark: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        文生图
        
        Args:
            prompt: 文本提示词
            size: 图像尺寸
            num_images: 生成图像数量
            watermark: 是否添加水印
            **kwargs: 其他参数
            
        Returns:
            API响应结果
        """
        if not self.client:
            return {
                "success": False,
                "error": "API客户端未初始化，请先设置API密钥",
                "images": [],
                "prompt": prompt
            }
            
        try:
            extra_body = {
                "watermark": watermark,
                **kwargs
            }
            
            # 如果需要生成多张图片
            if num_images > 1:
                extra_body.update({
                    "sequential_image_generation": "auto",
                    "sequential_image_generation_options": {
                        "max_images": num_images
                    }
                })
            else:
                extra_body["sequential_image_generation"] = "disabled"
            
            response = self.client.images.generate(
                model=self.config.get("api.model"),
                prompt=prompt,
                size=size,
                response_format="url",
                extra_body=extra_body
            )
            
            # 构建返回结果
            result = {
                "success": True,
                "images": [],
                "prompt": prompt,
                "model": self.config.get("api.model")
            }
            
            for image in response.data:
                result["images"].append({
                    "url": image.url,
                    "size": getattr(image, 'size', size)
                })
            
            self.logger.info(f"文生图成功，生成 {len(result['images'])} 张图片")
            return result
            
        except Exception as e:
            self.logger.error(f"文生图失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt
            }
    
    def image_to_image(
        self,
        prompt: str,
        image_paths: List[Union[str, Path]] = None,
        image_urls: List[str] = None,
        size: str = "2K",
        num_images: int = 1,
        watermark: bool = True,
        mode: str = "edit",  # "edit" 或 "generate"
        **kwargs
    ) -> Dict[str, Any]:
        """
        图生图/图像编辑
        
        Args:
            prompt: 文本提示词
            image_paths: 本地图像文件路径列表
            image_urls: 图像URL列表
            size: 输出图像尺寸
            num_images: 生成图像数量（仅在generate模式下有效）
            watermark: 是否添加水印
            mode: 模式，"edit"为图像编辑，"generate"为组图生成
            **kwargs: 其他参数
            
        Returns:
            API响应结果
        """
        if not self.client:
            return {
                "success": False,
                "error": "API客户端未初始化，请先设置API密钥",
                "images": [],
                "prompt": prompt
            }
            
        try:
            # 准备图像数据
            images = []
            
            # 处理本地文件
            if image_paths:
                for path in image_paths:
                    if Path(path).exists():
                        # 对于本地文件，我们将其上传或转换为URL
                        # 这里假设我们有一个方法将本地文件转换为可访问的URL
                        # 实际实现时可能需要上传到临时存储服务
                        images.append(str(path))  # 临时处理，实际需要转换为URL
            
            # 处理URL
            if image_urls:
                valid_urls = self._validate_image_urls(image_urls)
                images.extend(valid_urls)
            
            if not images:
                raise ValueError("必须提供至少一张图像")
            
            extra_body = {
                "image": images,
                "watermark": watermark,
                **kwargs
            }
            
            # 根据模式设置参数
            if mode == "generate" and num_images > 1:
                extra_body.update({
                    "sequential_image_generation": "auto",
                    "sequential_image_generation_options": {
                        "max_images": num_images
                    }
                })
            else:
                extra_body["sequential_image_generation"] = "disabled"
            
            response = self.client.images.generate(
                model=self.config.get("api.model"),
                prompt=prompt,
                size=size,
                response_format="url",
                extra_body=extra_body
            )
            
            # 构建返回结果
            result = {
                "success": True,
                "images": [],
                "prompt": prompt,
                "input_images": images,
                "mode": mode,
                "model": self.config.get("api.model")
            }
            
            for image in response.data:
                result["images"].append({
                    "url": image.url,
                    "size": getattr(image, 'size', size)
                })
            
            self.logger.info(f"图生图成功，输入 {len(images)} 张图片，生成 {len(result['images'])} 张图片")
            return result
            
        except Exception as e:
            self.logger.error(f"图生图失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "prompt": prompt,
                "input_images": images if 'images' in locals() else []
            }
    
    def video_generation(
        self,
        prompt: str,
        image_paths: List[Union[str, Path]] = None,
        image_urls: List[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        视频生成（预留接口）
        
        Args:
            prompt: 文本提示词
            image_paths: 本地图像文件路径列表
            image_urls: 图像URL列表
            **kwargs: 其他参数
            
        Returns:
            API响应结果
        """
        # 注意：此功能需要根据实际的Seedream视频生成API进行实现
        # 目前作为预留接口
        self.logger.warning("视频生成功能暂未实现")
        return {
            "success": False,
            "error": "视频生成功能暂未实现",
            "prompt": prompt
        }
    
    async def async_text_to_image(self, *args, **kwargs) -> Dict[str, Any]:
        """异步文生图"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.text_to_image, *args, **kwargs
        )
    
    async def async_image_to_image(self, *args, **kwargs) -> Dict[str, Any]:
        """异步图生图"""
        return await asyncio.get_event_loop().run_in_executor(
            None, self.image_to_image, *args, **kwargs
        )
    
    def test_connection(self) -> bool:
        """
        测试API连接
        
        Returns:
            连接是否成功
        """
        try:
            # 使用一个简单的文生图请求测试连接
            result = self.text_to_image(
                prompt="测试连接",
                size="1K"  # 使用较小尺寸节省配额
            )
            return result.get("success", False)
        except Exception as e:
            self.logger.error(f"API连接测试失败: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        获取当前模型信息
        
        Returns:
            模型信息
        """
        return {
            "model": self.config.get("api.model"),
            "base_url": self.config.get("api.base_url"),
            "supported_sizes": ["1K", "2K", "4K"],
            "supported_formats": ["url", "b64_json"],
            "features": {
                "text_to_image": True,
                "image_to_image": True,
                "image_editing": True,
                "sequential_generation": True,
                "video_generation": False  # 暂未支持
            }
        }


# 全局API客户端实例
api_client = SeedreamAPIClient()