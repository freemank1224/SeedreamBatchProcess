"""
文件处理模块
负责图像文件的读取、编码、下载、命名等操作
"""
import os
import base64
import hashlib
import logging
import requests
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
from urllib.parse import urlparse
from PIL import Image, ImageOps
import io

from ..utils.config import config_manager


class FileProcessor:
    """文件处理器"""
    
    def __init__(self):
        """初始化文件处理器"""
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        
        # 支持的图像格式
        self.supported_formats = self.config.get("image.supported_formats", [
            ".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp"
        ])
        
        # 最大文件大小（MB）
        self.max_size_mb = self.config.get("image.max_size_mb", 10)
    
    def validate_image_file(self, file_path: Union[str, Path]) -> Tuple[bool, str]:
        """
        验证图像文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            (是否有效, 错误信息)
        """
        try:
            file_path = Path(file_path)
            
            # 检查文件是否存在
            if not file_path.exists():
                return False, f"文件不存在: {file_path}"
            
            # 检查文件扩展名
            if file_path.suffix.lower() not in self.supported_formats:
                return False, f"不支持的文件格式: {file_path.suffix}"
            
            # 检查文件大小
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self.max_size_mb:
                return False, f"文件过大: {file_size_mb:.2f}MB > {self.max_size_mb}MB"
            
            # 尝试打开图像文件
            try:
                with Image.open(file_path) as img:
                    img.verify()
                return True, ""
            except Exception as e:
                return False, f"无效的图像文件: {e}"
                
        except Exception as e:
            return False, f"文件验证失败: {e}"
    
    def encode_image_to_base64(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        将图像文件编码为base64字符串
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            base64编码的字符串，失败时返回None
        """
        try:
            is_valid, error_msg = self.validate_image_file(file_path)
            if not is_valid:
                self.logger.error(f"图像验证失败: {error_msg}")
                return None
            
            with open(file_path, 'rb') as image_file:
                image_data = image_file.read()
                base64_string = base64.b64encode(image_data).decode('utf-8')
                
                self.logger.debug(f"图像编码成功: {file_path}")
                return base64_string
                
        except Exception as e:
            self.logger.error(f"图像编码失败: {file_path}, 错误: {e}")
            return None
    
    def decode_base64_to_image(
        self,
        base64_string: str,
        output_path: Union[str, Path],
        format: str = "PNG"
    ) -> bool:
        """
        将base64字符串解码为图像文件
        
        Args:
            base64_string: base64编码的图像数据
            output_path: 输出文件路径
            format: 图像格式
            
        Returns:
            是否成功
        """
        try:
            # 解码base64数据
            image_data = base64.b64decode(base64_string)
            
            # 创建图像对象
            image = Image.open(io.BytesIO(image_data))
            
            # 确保输出目录存在
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存图像
            image.save(output_path, format=format)
            
            self.logger.debug(f"图像解码成功: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"图像解码失败: {e}")
            return False
    
    def download_image_from_url(
        self,
        url: str,
        output_path: Union[str, Path],
        timeout: int = 30
    ) -> bool:
        """
        从URL下载图像
        
        Args:
            url: 图像URL
            output_path: 输出文件路径
            timeout: 超时时间（秒）
            
        Returns:
            是否成功
        """
        try:
            # 发送请求下载图像
            response = requests.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # 确保输出目录存在
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # 验证下载的文件
            is_valid, error_msg = self.validate_image_file(output_path)
            if not is_valid:
                output_path.unlink(missing_ok=True)  # 删除无效文件
                self.logger.error(f"下载的文件无效: {error_msg}")
                return False
            
            self.logger.info(f"图像下载成功: {url} -> {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"图像下载失败: {url}, 错误: {e}")
            return False
    
    def generate_filename(
        self,
        prefix: str = "",
        suffix: str = "",
        extension: str = ".png",
        include_timestamp: bool = True,
        include_uuid: bool = False
    ) -> str:
        """
        生成文件名
        
        Args:
            prefix: 前缀
            suffix: 后缀
            extension: 文件扩展名
            include_timestamp: 是否包含时间戳
            include_uuid: 是否包含UUID
            
        Returns:
            生成的文件名
        """
        parts = []
        
        if prefix:
            parts.append(prefix)
        
        if include_timestamp:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            parts.append(timestamp)
        
        if include_uuid:
            short_uuid = str(uuid.uuid4())[:8]
            parts.append(short_uuid)
        
        if suffix:
            parts.append(suffix)
        
        base_name = "_".join(parts) if parts else "image"
        return f"{base_name}{extension}"
    
    def create_unique_filename(
        self,
        output_dir: Union[str, Path],
        base_name: str,
        extension: str = ".png"
    ) -> str:
        """
        创建唯一的文件名（避免重复）
        
        Args:
            output_dir: 输出目录
            base_name: 基础文件名
            extension: 文件扩展名
            
        Returns:
            唯一的文件名
        """
        output_dir = Path(output_dir)
        base_path = output_dir / f"{base_name}{extension}"
        
        if not base_path.exists():
            return base_path.name
        
        # 如果文件已存在，添加数字后缀
        counter = 1
        while True:
            new_name = f"{base_name}_{counter}{extension}"
            new_path = output_dir / new_name
            if not new_path.exists():
                return new_name
            counter += 1
    
    def get_image_info(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        获取图像文件信息
        
        Args:
            file_path: 图像文件路径
            
        Returns:
            图像信息字典
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                return {"error": "文件不存在"}
            
            # 基本文件信息
            stat = file_path.stat()
            file_info = {
                "path": str(file_path),
                "name": file_path.name,
                "size_bytes": stat.st_size,
                "size_mb": stat.st_size / (1024 * 1024),
                "created": datetime.fromtimestamp(stat.st_ctime),
                "modified": datetime.fromtimestamp(stat.st_mtime),
            }
            
            # 图像信息
            try:
                with Image.open(file_path) as img:
                    file_info.update({
                        "width": img.width,
                        "height": img.height,
                        "format": img.format,
                        "mode": img.mode,
                        "has_transparency": img.mode in ("RGBA", "LA") or "transparency" in img.info
                    })
            except Exception as e:
                file_info["image_error"] = str(e)
            
            return file_info
            
        except Exception as e:
            return {"error": str(e)}
    
    def resize_image(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        max_width: int = 2048,
        max_height: int = 2048,
        quality: int = 95
    ) -> bool:
        """
        调整图像大小
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            max_width: 最大宽度
            max_height: 最大高度
            quality: 图像质量（1-100）
            
        Returns:
            是否成功
        """
        try:
            with Image.open(input_path) as img:
                # 计算新尺寸
                img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                
                # 确保输出目录存在
                output_path = Path(output_path)
                output_path.parent.mkdir(parents=True, exist_ok=True)
                
                # 保存图像
                save_kwargs = {}
                if output_path.suffix.lower() in ['.jpg', '.jpeg']:
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                
                img.save(output_path, **save_kwargs)
                
                self.logger.debug(f"图像调整成功: {input_path} -> {output_path}")
                return True
                
        except Exception as e:
            self.logger.error(f"图像调整失败: {e}")
            return False


class DirectoryScanner:
    """目录扫描器"""
    
    def __init__(self):
        """初始化目录扫描器"""
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self.file_processor = FileProcessor()
    
    def scan_directory(
        self,
        directory: Union[str, Path],
        recursive: bool = True,
        include_subdirs: bool = False
    ) -> Dict[str, Any]:
        """
        扫描目录中的图像文件
        
        Args:
            directory: 目录路径
            recursive: 是否递归扫描子目录
            include_subdirs: 是否在结果中包含子目录信息
            
        Returns:
            扫描结果
        """
        try:
            directory = Path(directory)
            
            if not directory.exists():
                return {"error": "目录不存在"}
            
            if not directory.is_dir():
                return {"error": "路径不是目录"}
            
            result = {
                "directory": str(directory),
                "total_files": 0,
                "valid_images": 0,
                "invalid_files": 0,
                "files": [],
                "errors": []
            }
            
            if include_subdirs:
                result["subdirectories"] = []
            
            # 获取文件列表
            if recursive:
                pattern = "**/*"
            else:
                pattern = "*"
            
            for item in directory.glob(pattern):
                if item.is_file():
                    result["total_files"] += 1
                    
                    # 检查是否为支持的图像格式
                    if item.suffix.lower() in self.file_processor.supported_formats:
                        is_valid, error_msg = self.file_processor.validate_image_file(item)
                        
                        file_info = {
                            "path": str(item),
                            "relative_path": str(item.relative_to(directory)),
                            "name": item.name,
                            "valid": is_valid
                        }
                        
                        if is_valid:
                            result["valid_images"] += 1
                            # 获取详细图像信息
                            image_info = self.file_processor.get_image_info(item)
                            file_info.update(image_info)
                        else:
                            result["invalid_files"] += 1
                            file_info["error"] = error_msg
                            result["errors"].append(f"{item}: {error_msg}")
                        
                        result["files"].append(file_info)
                
                elif include_subdirs and item.is_dir() and not recursive:
                    result["subdirectories"].append({
                        "path": str(item),
                        "name": item.name
                    })
            
            self.logger.info(f"目录扫描完成: {directory}, 找到 {result['valid_images']} 个有效图像文件")
            return result
            
        except Exception as e:
            error_msg = f"目录扫描失败: {e}"
            self.logger.error(error_msg)
            return {"error": error_msg}
    
    def get_directory_structure(self, directory: Union[str, Path], max_depth: int = 3) -> Dict[str, Any]:
        """
        获取目录结构
        
        Args:
            directory: 目录路径
            max_depth: 最大递归深度
            
        Returns:
            目录结构
        """
        try:
            directory = Path(directory)
            
            def _scan_recursive(path: Path, current_depth: int = 0) -> Dict[str, Any]:
                """递归扫描目录"""
                if current_depth > max_depth:
                    return {"truncated": True}
                
                node = {
                    "name": path.name,
                    "path": str(path),
                    "type": "directory",
                    "children": []
                }
                
                try:
                    for item in sorted(path.iterdir()):
                        if item.is_dir():
                            child = _scan_recursive(item, current_depth + 1)
                            node["children"].append(child)
                        elif item.suffix.lower() in self.file_processor.supported_formats:
                            node["children"].append({
                                "name": item.name,
                                "path": str(item),
                                "type": "image_file",
                                "size": item.stat().st_size
                            })
                except PermissionError:
                    node["error"] = "无权限访问"
                
                return node
            
            return _scan_recursive(directory)
            
        except Exception as e:
            return {"error": str(e)}


class PromptParser:
    """提示词解析器"""
    
    def __init__(self):
        """初始化提示词解析器"""
        self.logger = logging.getLogger(__name__)
    
    def parse_prompt_file(self, file_path: Union[str, Path]) -> List[str]:
        """
        解析提示词文件
        
        Args:
            file_path: 提示词文件路径
            
        Returns:
            提示词列表
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"文件不存在: {file_path}")
            
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 按行分割并清理
            prompts = [
                line.strip() 
                for line in content.split('\n') 
                if line.strip() and not line.strip().startswith('#')
            ]
            
            self.logger.info(f"解析提示词文件成功: {file_path}, 找到 {len(prompts)} 个提示词")
            return prompts
            
        except Exception as e:
            self.logger.error(f"解析提示词文件失败: {file_path}, 错误: {e}")
            return []
    
    def parse_csv_prompts(
        self,
        file_path: Union[str, Path],
        prompt_column: str = "prompt",
        delimiter: str = ","
    ) -> List[Dict[str, Any]]:
        """
        解析CSV格式的提示词文件
        
        Args:
            file_path: CSV文件路径
            prompt_column: 提示词列名
            delimiter: 分隔符
            
        Returns:
            提示词数据列表
        """
        try:
            import pandas as pd
            
            df = pd.read_csv(file_path, delimiter=delimiter)
            
            if prompt_column not in df.columns:
                raise ValueError(f"CSV文件中未找到列: {prompt_column}")
            
            # 转换为字典列表
            prompts = df.to_dict('records')
            
            self.logger.info(f"解析CSV提示词文件成功: {file_path}, 找到 {len(prompts)} 条记录")
            return prompts
            
        except Exception as e:
            self.logger.error(f"解析CSV提示词文件失败: {file_path}, 错误: {e}")
            return []


# 全局实例
file_processor = FileProcessor()
directory_scanner = DirectoryScanner()
prompt_parser = PromptParser()