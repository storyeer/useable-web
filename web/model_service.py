from modelscope import AutoModelForCausalLM, AutoTokenizer
import torch

class ModelService:
    def __init__(self, use_local=True, model_path=None):
        self.use_local = use_local
        if use_local and model_path:
            print("正在加载本地模型...")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained(model_path)
                
                # 加载模型
                self.model = AutoModelForCausalLM.from_pretrained(
                    model_path,
                    torch_dtype="auto",
                    device_map="auto"
                )
                
                print("模型加载完成")
            except Exception as e:
                print(f"模型加载错误: {str(e)}")
                raise

    def generate_answer(self, question):
        try:
            if not self.use_local:
                return {"success": False, "error": "未配置模型服务"}

            print(f"开始处理问题: {question}")
            
            try:
                # 构建消息
                messages = [
                    {"role": "system", "content": "你是一个专业的审计助手。"},
                    {"role": "user", "content": question}
                ]
                
                # 应用聊天模板
                text = self.tokenizer.apply_chat_template(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True
                )
                
                # 准备模型输入
                model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
                
                # 生成回答
                generated_ids = self.model.generate(
                    **model_inputs,
                    max_new_tokens=512,
                    temperature=0.7,
                    top_p=0.9
                )
                
                # 提取新生成的token
                generated_ids = [
                    output_ids[len(input_ids):] 
                    for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
                ]
                
                # 解码回答
                response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
                print(f"生成的回答: {response}")
                
                return {
                    "success": True,
                    "answer": response
                }
            except Exception as e:
                print(f"生成回答时出错: {str(e)}")
                raise
            
        except Exception as e:
            print(f"模型生成错误: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 