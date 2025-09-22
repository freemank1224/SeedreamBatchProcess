"""
最简单的测试界面
"""
import gradio as gr

def create_minimal_interface():
    """创建最简单的界面"""
    
    def greet(name):
        return f"Hello {name}!"
    
    interface = gr.Interface(
        fn=greet,
        inputs=gr.Textbox(label="输入你的名字"),
        outputs=gr.Textbox(label="问候"),
        title="测试界面"
    )
    
    return interface