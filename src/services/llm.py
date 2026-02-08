import time
import threading

# 全局锁，用于控制 API 调用频率
api_lock = threading.Lock()
LAST_API_CALL_TIME = 0

def generate_with_llm(prompt, client, model, max_retries=3):
    """调用 LLM 生成文本 (硅基流动 API，关闭思考模式)"""
    global LAST_API_CALL_TIME
    
    for attempt in range(max_retries):
        try:
            with api_lock:
                elapsed = time.time() - LAST_API_CALL_TIME
                if elapsed < 1.0:
                    time.sleep(1.0 - elapsed)
                LAST_API_CALL_TIME = time.time()
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200,
                timeout=30,  # 30秒超时，防止线程卡死
                extra_body={"enable_thinking": False}
            )
            
            message = response.choices[0].message
            result = message.content
            
            if result is None:
                return "[Error: Empty response from model]"
            
            # 返回完整结果（保留多行），只做基本清理
            result = result.strip()
            
            return result if result else "[Error: Empty content]"
            
        except Exception as e:
            error_str = str(e)
            if '429' in error_str:
                wait_time = (2 ** attempt) * 3
                time.sleep(wait_time)
                continue
            return f"[Error: {error_str}]"
    
    return "[Error: Max retries exceeded]"
