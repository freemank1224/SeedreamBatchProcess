"""
Seedream 批处理应用主程序入口
"""
import os
import sys
import logging
import argparse
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.ui.main_interface import seedream_ui
from src.utils.config import config_manager
from src.api.client import api_client
from src.batch import task_scheduler


def setup_logging():
    """设置日志系统"""
    # 确保日志目录存在
    log_dir = config_manager.get_absolute_path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # 配置日志格式
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # 获取日志级别
    log_level = config_manager.get("logging.level", "INFO")
    
    # 配置根日志器
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format=log_format,
        handlers=[
            # 控制台输出
            logging.StreamHandler(sys.stdout),
            # 文件输出
            logging.FileHandler(
                log_dir / "seedream_app.log",
                encoding='utf-8'
            )
        ]
    )
    
    # 设置第三方库日志级别
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("PIL").setLevel(logging.WARNING)


def initialize_application():
    """初始化应用程序"""
    logger = logging.getLogger(__name__)
    
    try:
        # 创建必要的目录
        config_manager.create_directories()
        logger.info("目录结构检查完成")
        
        # 检查API密钥
        if not config_manager.validate_api_key():
            logger.warning("API密钥未配置，请在界面中设置")
        else:
            logger.info("API密钥验证通过")
        
        # 初始化组件
        logger.info("应用程序初始化完成")
        
        return True
        
    except Exception as e:
        logger.error(f"应用程序初始化失败: {e}")
        return False


def create_sample_files():
    """创建示例文件"""
    logger = logging.getLogger(__name__)
    
    try:
        # 创建示例提示词文件
        sample_prompts = """# 示例提示词文件
# 每行一个提示词，以#开头的行为注释

一只可爱的小猫在花园里玩耍
美丽的日落景色，海边的沙滩
现代风格的建筑设计，玻璃幕墙
传统中式庭院，小桥流水
科幻风格的城市，未来感十足"""
        
        sample_file = config_manager.get_absolute_path("input") / "sample_prompts.txt"
        if not sample_file.exists():
            with open(sample_file, 'w', encoding='utf-8') as f:
                f.write(sample_prompts)
            logger.info(f"创建示例提示词文件: {sample_file}")
        
        # 创建说明文件
        readme_content = """# Seedream 批处理应用

## 使用说明

1. **配置API密钥**
   - 在"系统配置"面板中输入您的 ARK API Key
   - 点击"保存密钥"按钮
   - 点击"测试连接"验证API可用性

2. **文生图功能**
   - 在"文生图"标签页输入提示词
   - 选择图像尺寸和生成数量
   - 点击"生成图像"开始生成

3. **批量处理**
   - 可以输入多行提示词或上传提示词文件
   - 支持 .txt 和 .csv 格式
   - 设置输出目录后点击"批量生成"

4. **图生图功能**
   - 上传图像文件或指定图像目录
   - 输入编辑指令描述想要的修改
   - 选择处理模式和输出尺寸
   - 点击"处理图像"开始处理

5. **批处理管理**
   - 在"批处理管理"标签页控制队列
   - 可以开始、暂停、停止批处理
   - 查看任务状态和进度

6. **进度监控**
   - 在"进度监控"标签页查看实时进度
   - 查看系统日志和任务统计

## 目录结构

- `input/`: 输入文件目录
- `output/`: 输出文件目录
- `config/`: 配置文件目录
- `logs/`: 日志文件目录

## 注意事项

- 请确保API密钥有效且有足够的配额
- 批处理时建议设置合理的并发数量
- 大量任务处理时请注意磁盘空间
"""
        
        readme_file = project_root / "README.md"
        if not readme_file.exists():
            with open(readme_file, 'w', encoding='utf-8') as f:
                f.write(readme_content)
            logger.info(f"创建说明文件: {readme_file}")
        
    except Exception as e:
        logger.error(f"创建示例文件失败: {e}")


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="Seedream 批处理应用")
    parser.add_argument(
        "--port", 
        type=int, 
        default=7860,
        help="Web界面端口号 (默认: 7860)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Web界面主机地址 (默认: 127.0.0.1)"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="创建公共分享链接"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logging()
    logger = logging.getLogger(__name__)
    
    logger.info("=" * 50)
    logger.info("Seedream 批处理应用启动")
    logger.info("=" * 50)
    
    # 初始化应用
    if not initialize_application():
        logger.error("应用程序初始化失败，退出")
        sys.exit(1)
    
    # 创建示例文件
    create_sample_files()
    
    try:
        # 创建并启动界面
        interface = seedream_ui.create_interface()
        
        logger.info(f"启动Web界面...")
        logger.info(f"地址: http://{args.host}:{args.port}")
        
        if args.share:
            logger.info("启用公共分享链接")
        
        # 启动界面
        interface.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            debug=args.debug,
            show_error=True,
            quiet=False,
            inbrowser=True
        )
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭应用...")
    except Exception as e:
        logger.error(f"应用运行时出错: {e}")
        sys.exit(1)
    finally:
        # 清理资源
        if task_scheduler.is_running:
            logger.info("正在停止任务调度器...")
            task_scheduler.stop()
        
        logger.info("应用程序已退出")


if __name__ == "__main__":
    main()