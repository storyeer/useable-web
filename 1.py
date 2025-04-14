#模型下载
from modelscope import snapshot_download
model_dir = snapshot_download('LLM-Research/gemma-3-27b-it',cache_dir='D:\DMX\gemma-3-27b-it')
print(f"模型下载完成，路径为：{model_dir}")
