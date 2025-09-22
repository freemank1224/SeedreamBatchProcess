"""
配置管理模块
负责处理应用程序的配置，包括API密钥管理、用户设置等
"""
import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: str = "config"):
        """
        初始化配置管理器
        
        Args:
            config_dir: 配置文件目录
        """
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 配置文件路径
        self.env_file = self.config_dir / ".env"
        self.config_file = self.config_dir / "config.yaml"
        self.default_config_file = self.config_dir / "default_config.yaml"
        
        # 加载环境变量
        load_dotenv(self.env_file)
        
        # 初始化配置
        self._init_default_config()
        self._load_config()
    
    def _init_default_config(self) -> None:
        """初始化默认配置"""
        default_config = {
            "api": {
                "base_url": "https://ark.cn-beijing.volces.com/api/v3",
                "model": "doubao-seedream-4-0-250828",
                "timeout": 30,
                "max_retries": 3
            },
            "batch": {
                "max_concurrent_tasks": 5,
                "batch_size": 10,
                "auto_retry": True,
                "retry_delay": 5
            },
            "image": {
                "supported_formats": [".jpg", ".jpeg", ".png", ".bmp", ".tiff"],
                "max_size_mb": 10,
                "default_size": "2K",
                "output_format": "png"
            },
            "paths": {
                "input_dir": "input",
                "output_dir": "output",
                "logs_dir": "logs",
                "cache_dir": "cache"
            },
            "ui": {
                "theme": "default",
                "share": False,
                "port": 7860,
                "height": 600
            },
            "logging": {
                "level": "INFO",
                "file_enabled": True,
                "console_enabled": True,
                "max_file_size_mb": 10
            }
        }
        
        # 写入默认配置文件
        if not self.default_config_file.exists():
            with open(self.default_config_file, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
    
    def _load_config(self) -> None:
        """加载配置"""
        # 首先加载默认配置
        with open(self.default_config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)
        
        # 如果存在用户配置文件，则覆盖默认配置
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                user_config = yaml.safe_load(f)
                if user_config:
                    self._deep_update(self.config, user_config)
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """深度更新字典"""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key_path: 配置键路径，如 'api.base_url'
            default: 默认值
            
        Returns:
            配置值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key_path: 配置键路径，如 'api.base_url'
            value: 配置值
        """
        keys = key_path.split('.')
        config = self.config
        
        # 导航到最后一级
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置值
        config[keys[-1]] = value
        
        # 保存配置
        self.save_config()
    
    def save_config(self) -> None:
        """保存用户配置"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            yaml.dump(self.config, f, default_flow_style=False, allow_unicode=True)
    
    def get_api_key(self) -> Optional[str]:
        """
        获取API密钥
        
        Returns:
            API密钥，如果未设置则返回None
        """
        # 优先从环境变量获取
        api_key = os.getenv("ARK_API_KEY")
        if api_key:
            return api_key
        
        # 从配置文件获取
        return self.get("api.api_key")
    
    def set_api_key(self, api_key: str, save_to_env: bool = True) -> None:
        """
        设置API密钥
        
        Args:
            api_key: API密钥
            save_to_env: 是否保存到环境变量文件
        """
        if save_to_env:
            # 更新.env文件
            env_content = ""
            if self.env_file.exists():
                with open(self.env_file, 'r', encoding='utf-8') as f:
                    env_content = f.read()
            
            # 检查是否已存在ARK_API_KEY
            lines = env_content.split('\n')
            updated = False
            for i, line in enumerate(lines):
                if line.startswith('ARK_API_KEY='):
                    lines[i] = f'ARK_API_KEY={api_key}'
                    updated = True
                    break
            
            if not updated:
                lines.append(f'ARK_API_KEY={api_key}')
            
            # 写回文件
            with open(self.env_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(lines))
            
            # 更新当前环境变量
            os.environ['ARK_API_KEY'] = api_key
        else:
            # 只保存到配置文件
            self.set("api.api_key", api_key)
    
    def validate_api_key(self) -> bool:
        """
        验证API密钥是否有效
        
        Returns:
            是否有效
        """
        api_key = self.get_api_key()
        return api_key is not None and len(api_key.strip()) > 0
    
    def get_absolute_path(self, relative_path: str) -> Path:
        """
        获取相对于项目根目录的绝对路径
        
        Args:
            relative_path: 相对路径
            
        Returns:
            绝对路径
        """
        # 假设配置目录在项目根目录下
        project_root = self.config_dir.parent
        return project_root / relative_path
    
    def create_directories(self) -> None:
        """创建必要的目录"""
        dirs = [
            self.get("paths.input_dir"),
            self.get("paths.output_dir"),
            self.get("paths.logs_dir"),
            self.get("paths.cache_dir", "cache")
        ]
        
        for dir_path in dirs:
            if dir_path:
                abs_path = self.get_absolute_path(dir_path)
                abs_path.mkdir(parents=True, exist_ok=True)
    
    def export_config(self, file_path: str) -> None:
        """
        导出配置到文件
        
        Args:
            file_path: 导出文件路径
        """
        # 创建一个安全的配置副本（不包含敏感信息）
        safe_config = self.config.copy()
        if "api" in safe_config and "api_key" in safe_config["api"]:
            safe_config["api"]["api_key"] = "***HIDDEN***"
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(safe_config, f, default_flow_style=False, allow_unicode=True)
    
    def import_config(self, file_path: str) -> None:
        """
        从文件导入配置
        
        Args:
            file_path: 配置文件路径
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            imported_config = yaml.safe_load(f)
            if imported_config:
                self._deep_update(self.config, imported_config)
                self.save_config()


# 全局配置管理器实例
config_manager = ConfigManager()