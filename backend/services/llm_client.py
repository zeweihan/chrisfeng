"""LLM client for multi-provider API calls with detailed logging."""
import httpx
import json
import time
import traceback
from config import settings

# Simple logger that prints with timestamps
def _log(msg: str):
    ts = time.strftime("%H:%M:%S")
    print(f"[LLM {ts}] {msg}", flush=True)


async def call_llm(
    prompt: str,
    system_prompt: str = None,
    provider: str = "google",
    model: str = "gemini-3.1-pro-preview",
    temperature: float = 0.3,
    max_tokens: int = 32768,
) -> str:
    """Call LLM dynamically integrating 3 native schemas."""
    model_str = model
    
    _log(f">>> Starting LLM call: provider={provider}, model={model_str}")
    _log(f"    prompt_len={len(prompt)}, system_prompt_len={len(system_prompt or '')}, max_tokens={max_tokens}")
    start_time = time.time()
    
    if provider == "google":
        model_str = model_str.replace("google/", "")
        
        if not settings.GEMINI_API_KEY:
            raise Exception("Google API (Gemini) key is not configured. Please check your .env file on the server.")
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_str}:generateContent?key={settings.GEMINI_API_KEY[:8]}..."
        _log(f"    Google API URL: {url}")
        
        real_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_str}:generateContent?key={settings.GEMINI_API_KEY}"
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": min(max_tokens, 8192)},
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                _log(f"    Sending request to Google API...")
                response = await client.post(real_url, headers=headers, json=payload)
                elapsed = time.time() - start_time
                _log(f"    Response received: status={response.status_code}, elapsed={elapsed:.1f}s")
                data = response.json()
                if response.status_code != 200:
                    err_msg = data.get('error', {}).get('message', str(data)[:500])
                    _log(f"    ❌ Google API error: {err_msg}")
                    raise Exception(f"Google API error {response.status_code}: {err_msg}")
                try:
                    result = data["candidates"][0]["content"]["parts"][0]["text"]
                    _log(f"    ✅ Success! Response length: {len(result)} chars")
                    return result
                except Exception:
                    _log(f"    ❌ Invalid response structure: {str(data)[:500]}")
                    raise Exception(f"Invalid Google API response: {str(data)[:500]}")
        except httpx.TimeoutException as e:
            elapsed = time.time() - start_time
            _log(f"    ❌ TIMEOUT after {elapsed:.1f}s: {e}")
            raise Exception(f"Google API timeout after {elapsed:.0f}s")
        except Exception as e:
            if "Google API error" not in str(e) and "timeout" not in str(e).lower():
                _log(f"    ❌ Unexpected error: {traceback.format_exc()}")
            raise

    elif provider in ["openrouter", "kimi"]:
        if provider == "openrouter":
            url = f"{settings.OPENROUTER_BASE_URL}/chat/completions"
            api_key = settings.OPENROUTER_API_KEY
        else: # Kimi
            url = "https://api.moonshot.cn/v1/chat/completions"
            api_key = settings.KIMI_API_KEY
            if model_str == "moonshot-v1-32k" or model_str == "kimi-k2.5":
                model_str = "kimi-k2.5"

        if not api_key:
            raise Exception(f"{provider.title()} API key is not configured. Please check your .env file on the server.")


        _log(f"    API URL: {url}")
        _log(f"    Model: {model_str}")
        
        headers = {
            "Authorization": f"Bearer {api_key[:8]}...",
            "Content-Type": "application/json"
        }
        real_headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        if provider == "openrouter":
            real_headers["HTTP-Referer"] = "https://hr-report.local"
            real_headers["X-Title"] = "HR Report Generator"
            
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        _log(f"    Messages: {len(messages)} messages, total content ~{sum(len(m['content']) for m in messages)} chars")
        
        payload = {
            "model": model_str,
            "messages": messages,
            "max_tokens": max_tokens,
            "stream": True,  # Use streaming to prevent 60s idle timeout disconnects
        }
        
        # Only OpenRouter generally supports ad-hoc temperatures. Kimi 2.5 strictly requires it omitted or 1.0.
        if provider == "openrouter":
            payload["temperature"] = temperature

        try:
            async with httpx.AsyncClient(timeout=600.0) as client:
                _log(f"    Sending request to {provider.title()} API (Streaming Mode)...")
                
                # Use streaming to keep connection alive
                async with client.stream("POST", url, headers=real_headers, json=payload) as response:
                    elapsed = time.time() - start_time
                    _log(f"    Headers received: status={response.status_code}, wait={elapsed:.1f}s")
                    
                    if response.status_code != 200:
                        err_text = await response.aread()
                        err_msg = json.loads(err_text).get('error', {}).get('message', str(err_text)[:500])
                        _log(f"    ❌ {provider.title()} API error: {err_msg}")
                        raise Exception(f"{provider.title()} API error {response.status_code}: {err_msg}")
                    
                    collected_chunks = []
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                delta = chunk["choices"][0]["delta"].get("content", "")
                                if delta:
                                    collected_chunks.append(delta)
                            except json.JSONDecodeError:
                                pass
                    
                    result = "".join(collected_chunks)
                    _log(f"    ✅ Success! Stream completed. Total response length: {len(result)} chars")
                    return result
        except httpx.TimeoutException as e:
            elapsed = time.time() - start_time
            _log(f"    ❌ TIMEOUT after {elapsed:.1f}s: {e}")
            raise Exception(f"{provider.title()} API timeout after {elapsed:.0f}s")
        except Exception as e:
            if "API error" not in str(e) and "timeout" not in str(e).lower():
                _log(f"    ❌ Unexpected error: {traceback.format_exc()}")
            raise
    else:
        raise Exception(f"Unsupported provider: {provider}")


async def get_configured_prompt(db, key: str) -> str:
    """Get a prompt template from admin config."""
    from database import AdminConfig
    config = db.query(AdminConfig).filter_by(key=key).first()
    return config.value if config else ""


async def analyze_with_llm(system_prompt: str, data_str: str, section_prompt: str, db=None, provider="google", model="gemini-3.1-pro-preview") -> str:
    """Combine system + section prompt + data, call LLM."""
    full_prompt = f"{section_prompt}\n\n---\n数据如下：\n{data_str}\n\n请生成分析洞察（Key Findings），每条用 **加粗标题** + 详细说明的格式。"
    _log(f"analyze_with_llm: data_str={len(data_str)} chars, section_prompt={len(section_prompt)} chars, full_prompt={len(full_prompt)} chars")
    return await call_llm(full_prompt, system_prompt=system_prompt, provider=provider, model=model)
