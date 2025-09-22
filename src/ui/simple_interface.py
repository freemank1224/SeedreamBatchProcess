"""
简化版本的Gradio界面用于测试
"""
import gradio as gr
import logging
from ..api.client import api_client

def create_simple_interface():
    """创建简化版界面"""
    
    with gr.Blocks(title="Seedream 批处理应用", theme=gr.themes.Soft()) as interface:
        
        # 标题
        gr.Markdown("# 🎨 Seedream 批处理应用")
        
        # API密钥配置
        with gr.Accordion("⚙️ API配置", open=True):
            with gr.Row():
                api_key_input = gr.Textbox(
                    label="API密钥",
                    type="password",
                    placeholder="请输入Seedream API密钥"
                )
                save_btn = gr.Button("保存配置")
        
        # 文生图功能
        with gr.Tab("📝 文生图"):
            with gr.Row():
                with gr.Column():
                    prompt_input = gr.Textbox(
                        label="描述提示词",
                        placeholder="请输入图像描述...",
                        lines=3
                    )
                    generate_btn = gr.Button("生成图像", variant="primary")
                
                with gr.Column():
                    output_image = gr.Image(label="生成结果")
        
        # 状态显示
        status_text = gr.Textbox(label="状态", value="就绪")
        
        # 事件绑定
        def save_api_key(api_key):
            if api_key.strip():
                api_client.set_api_key(api_key.strip())
                return "API密钥保存成功"
            return "请输入有效的API密钥"
        
        def generate_image(prompt):
            if not prompt.strip():
                return None, "请输入描述提示词"
            
            try:
                # 这里暂时返回占位符
                return None, f"正在生成图像: {prompt[:50]}..."
            except Exception as e:
                return None, f"生成失败: {str(e)}"
        
        save_btn.click(
            fn=save_api_key,
            inputs=[api_key_input],
            outputs=[status_text]
        )
        
        generate_btn.click(
            fn=generate_image,
            inputs=[prompt_input],
            outputs=[output_image, status_text]
        )
    
    return interface