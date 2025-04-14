from modelscope import AutoModelForCausalLM, AutoTokenizer
import torch

class LocalModelService:
    def __init__(self, model_path):
        self.model_path = model_path
        print(f"正在从 {model_path} 加载模型...")
        
        # 加载 tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(
            model_path,
            trust_remote_code=True
        )
        
        # 加载模型
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype="auto",
            device_map="auto",
            trust_remote_code=True
        )
        self.model.eval()
        print("模型加载完成")

    def generate_answer(self, question):
        try:
            # 构建对话消息
            messages = [
                {
                    "role": "system",
                    "content": "你是一个专业的审计助手，请用中文回答问题。"
                },
                {
                    "role": "user",
                    "content": question
                }
            ]

            # 使用 chat template
            text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )
            
            # 准备输入
            model_inputs = self.tokenizer([text], return_tensors="pt").to(self.model.device)
            
            # 生成回答
            generated_ids = self.model.generate(
                **model_inputs,
                max_new_tokens=512,
                temperature=0.7,
                top_p=0.9
            )
            
            # 只获取新生成的token
            generated_ids = [
                output_ids[len(input_ids):] 
                for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)
            ]
            
            # 解码回答
            response = self.tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]
            
            return {
                "success": True,
                "answer": response
            }

        except Exception as e:
            print(f"生成回答失败: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            } 