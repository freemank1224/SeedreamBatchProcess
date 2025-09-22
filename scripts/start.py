#!/usr/bin/env python3
"""
Seedream 批处理应用一键启动脚本
"""
import os
import sys
import subprocess
import platform
from pathlib import Path


def check_python_version():
    """检查Python版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ 错误: 需要 Python 3.8 或更高版本")
        print(f"当前版本: Python {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python版本检查通过: {version.major}.{version.minor}.{version.micro}")
    return True


def check_virtual_environment():
    """检查虚拟环境"""
    venv_path = Path("venv")
    
    if not venv_path.exists():
        print("⚠️  未找到虚拟环境，正在创建...")
        try:
            subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
            print("✅ 虚拟环境创建成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ 虚拟环境创建失败: {e}")
            return False
    else:
        print("✅ 虚拟环境已存在")
    
    return True


def get_venv_python():
    """获取虚拟环境的Python路径"""
    system = platform.system().lower()
    
    if system == "windows":
        return Path("venv") / "Scripts" / "python.exe"
    else:
        return Path("venv") / "bin" / "python"


def install_dependencies():
    """安装依赖包"""
    python_path = get_venv_python()
    
    if not python_path.exists():
        print("❌ 虚拟环境Python解释器未找到")
        return False
    
    print("📦 正在安装依赖包...")
    try:
        # 升级pip
        subprocess.run([
            str(python_path), "-m", "pip", "install", "--upgrade", "pip"
        ], check=True, capture_output=True)
        
        # 安装依赖
        subprocess.run([
            str(python_path), "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)
        
        print("✅ 依赖包安装完成")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ 依赖包安装失败: {e}")
        return False


def create_directories():
    """创建必要的目录"""
    directories = ["input", "output", "logs", "config"]
    
    for dir_name in directories:
        dir_path = Path(dir_name)
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"📁 创建目录: {dir_name}")
    
    print("✅ 目录结构检查完成")


def check_api_key():
    """检查API密钥配置"""
    env_file = Path("config") / ".env"
    
    if env_file.exists():
        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if "ARK_API_KEY=" in content:
                print("✅ 发现API密钥配置")
                return True
    
    print("⚠️  未发现API密钥配置，请在应用启动后在界面中设置")
    return True  # 不阻止启动


def show_startup_info():
    """显示启动信息"""
    print("\n" + "="*60)
    print("🎨 Seedream 批处理应用")
    print("="*60)
    print("基于 Seedream API 的图像批处理工具")
    print("支持文生图、图生图、图像编辑等功能")
    print("="*60)


def main():
    """主函数"""
    show_startup_info()
    
    print("\n🔧 正在进行环境检查...")
    
    # 检查Python版本
    if not check_python_version():
        input("按回车键退出...")
        sys.exit(1)
    
    # 检查虚拟环境
    if not check_virtual_environment():
        input("按回车键退出...")
        sys.exit(1)
    
    # 安装依赖
    if not install_dependencies():
        input("按回车键退出...")
        sys.exit(1)
    
    # 创建目录
    create_directories()
    
    # 检查API密钥
    check_api_key()
    
    print("\n🚀 正在启动应用...")
    print("请稍等，首次启动可能需要一些时间...")
    
    # 启动应用
    python_path = get_venv_python()
    
    try:
        # 启动主程序
        result = subprocess.run([
            str(python_path), "main.py"
        ], cwd=Path.cwd())
        
        if result.returncode != 0:
            print(f"❌ 应用启动失败，退出码: {result.returncode}")
    
    except KeyboardInterrupt:
        print("\n⏹️  应用已停止")
    
    except Exception as e:
        print(f"❌ 启动过程中出现错误: {e}")
    
    finally:
        print("\n👋 感谢使用 Seedream 批处理应用！")
        input("按回车键退出...")


if __name__ == "__main__":
    main()