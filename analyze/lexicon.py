"""Seed lexicon: stable entities/concepts with tags + official URLs. Dynamic candidates are discovered separately.
Entry: canonical -> (aliases, tags, vendor, official_url). Names not present here are still discovered from data.
Primary tag = first tag.
"""

L = {}


def add(name, aliases, tags, vendor=None, url=None):
    L[name] = {"aliases": aliases, "tags": tags.split(","), "vendor": vendor, "url": url}


# vendors
add("OpenAI", ["openai"], "vendor,models", "OpenAI", "https://openai.com/")
add("Anthropic", ["anthropic"], "vendor,models", "Anthropic", "https://www.anthropic.com/")
add("Google DeepMind", ["deepmind", "google deepmind"], "vendor,research", "Google", "https://deepmind.google/")
add("Meta AI", ["meta ai", "meta superintelligence"], "vendor,models", "Meta", "https://ai.meta.com/")
add("Mistral AI", ["mistral ai"], "vendor,models", "Mistral", "https://mistral.ai/")
add("xAI", ["xai"], "vendor,models", "xAI", "https://x.ai/")
add("Microsoft Foundry", ["microsoft foundry", "azure ai foundry"], "vendor,tools", "Microsoft", "https://learn.microsoft.com/azure/ai-foundry/")
add("Alibaba Qwen", ["alibaba qwen", "qwen team"], "vendor,models", "Alibaba", "https://qwenlm.github.io/")
add("Moonshot AI", ["moonshot ai", "moonshot"], "vendor,models", "Moonshot", "https://www.moonshot.ai/")
add("Hugging Face", ["hugging face", "huggingface"], "vendor,tools", "HuggingFace", "https://huggingface.co/")
# local LLM runtimes / formats
add("Ollama", ["ollama"], "local-llm,tools", "Ollama", "https://ollama.com/")
add("llama.cpp", ["llama cpp", "llamacpp", "llama.cpp"], "local-llm,tools", "ggml", "https://github.com/ggml-org/llama.cpp")
add("LM Studio", ["lm studio", "lmstudio"], "local-llm,tools", "LMStudio", "https://lmstudio.ai/")
add("vLLM", ["vllm"], "local-llm,tools", "vLLM", "https://github.com/vllm-project/vllm")
add("SGLang", ["sglang"], "local-llm,tools", "SGLang", "https://github.com/sgl-project/sglang")
add("MLX", ["mlx", "mlx lm"], "local-llm,hardware", "Apple", "https://github.com/ml-explore/mlx")
add("GGUF", ["gguf"], "local-llm,tools", "ggml", "https://github.com/ggml-org/ggml/blob/master/docs/gguf.md")
add("Unsloth", ["unsloth"], "local-llm,tools", "Unsloth", "https://unsloth.ai/")
add("Open WebUI", ["open webui"], "local-llm,tools", "OpenWebUI", "https://openwebui.com/")
add("Quantization", ["quantization", "quantized", "nvfp4", "mxfp4", "int4", "q4 k m"], "local-llm,research", None, None)
add("Speculative decoding", ["speculative decoding", "mtp", "multi token prediction"], "local-llm,research", None, None)
# hardware
add("NVIDIA DGX Spark", ["dgx spark"], "hardware,local-llm", "NVIDIA", "https://www.nvidia.com/en-us/products/workstations/dgx-spark/")
add("NVIDIA Blackwell", ["blackwell", "rtx 50", "rtx 5090", "rtx pro 6000"], "hardware", "NVIDIA", "https://www.nvidia.com/en-us/data-center/technologies/blackwell-architecture/")
add("AMD Strix Halo", ["strix halo", "ryzen ai max"], "hardware,local-llm", "AMD", "https://www.amd.com/en/products/processors/laptop/ryzen/ai-300-series.html")
add("Apple Silicon", ["apple silicon", "mac studio", "m3 ultra", "m4 max", "m5"], "hardware,local-llm", "Apple", "https://www.apple.com/mac/")
add("NVIDIA Jetson", ["jetson thor", "jetson orin"], "hardware", "NVIDIA", "https://developer.nvidia.com/embedded-computing")
add("Cerebras", ["cerebras"], "hardware,vendor", "Cerebras", "https://www.cerebras.ai/")
add("Groq", ["groq"], "hardware,vendor", "Groq", "https://groq.com/")
add("Google TPU", ["tpu", "ironwood"], "hardware", "Google", "https://cloud.google.com/tpu")
# agents / tools
add("MCP", ["mcp", "model context protocol", "mcp server"], "agents,tools", "Anthropic", "https://modelcontextprotocol.io/")
add("Claude Code", ["claude code"], "agents,tools", "Anthropic", "https://www.anthropic.com/claude-code")
add("OpenAI Codex", ["openai codex", "codex cli", "codex"], "agents,tools", "OpenAI", "https://developers.openai.com/codex")
add("Cursor", ["cursor ai", "cursor ide", "cursor"], "agents,tools", "Cursor", "https://cursor.com/")
add("GitHub Copilot", ["github copilot", "copilot cli"], "agents,tools", "Microsoft", "https://github.com/features/copilot")
add("Gemini CLI", ["gemini cli"], "agents,tools", "Google", "https://github.com/google-gemini/gemini-cli")
add("OpenHands", ["openhands"], "agents,tools", "OpenHands", "https://github.com/All-Hands-AI/OpenHands")
add("Cline", ["cline"], "agents,tools", "Cline", "https://cline.bot/")
add("LangGraph", ["langgraph"], "agents,tools", "LangChain", "https://www.langchain.com/langgraph")
add("LangChain", ["langchain"], "tools,agents", "LangChain", "https://www.langchain.com/")
add("CrewAI", ["crewai"], "agents,tools", "CrewAI", "https://www.crewai.com/")
add("n8n", ["n8n"], "tools,agents", "n8n", "https://n8n.io/")
add("Dify", ["dify"], "tools,agents", "Dify", "https://dify.ai/")
add("A2A protocol", ["a2a", "agent2agent"], "agents", "Google", "https://a2a-protocol.org/")
add("Agent Skills", ["agent skills", "skill md", "agents md"], "agents", None, "https://agentskills.io/")
add("RAG", ["rag", "retrieval augmented generation"], "tools,research", None, None)
add("OpenCode", ["opencode"], "agents,tools", "OpenCode", "https://opencode.ai/")
add("ComfyUI", ["comfyui"], "tools", "ComfyUI", "https://www.comfy.org/")
# research concepts
add("Mixture of Experts", ["mixture of experts", "moe"], "research,models", None, None)
add("Reinforcement learning (RLVR)", ["rlvr", "grpo", "reinforcement learning"], "research", None, None)
add("Diffusion language models", ["diffusion language model", "dllm", "diffusion llm"], "research,models", None, None)
add("Test-time compute", ["test time compute", "reasoning model"], "research,models", None, None)

# vendor detection for dynamic candidates (token/prefix patterns on lowercase name or HF org)
VENDOR_PATTERNS = {
    "Alibaba": ["qwen", "alibaba", "wan"], "Google": ["gemma", "gemini", "google", "embeddinggemma", "veo", "imagen"],
    "Meta": ["llama", "meta-llama", "facebook"], "OpenAI": ["gpt", "openai", "sora", "whisper", "o3", "o4"],
    "Anthropic": ["claude", "anthropic", "sonnet", "opus", "haiku"], "DeepSeek": ["deepseek"],
    "Mistral": ["mistral", "mixtral", "devstral", "magistral", "ministral"], "Microsoft": ["phi", "microsoft", "copilot"],
    "Moonshot": ["kimi", "moonshot"], "Zhipu": ["glm", "zai", "z-ai", "zhipu"], "MiniMax": ["minimax"],
    "xAI": ["grok", "xai", "x-ai"], "NVIDIA": ["nvidia", "nemotron", "cosmos"], "BlackForestLabs": ["flux", "black-forest"],
    "StabilityAI": ["stability", "stable-diffusion", "sdxl"], "IBM": ["granite", "ibm"], "Tencent": ["hunyuan", "tencent"],
    "ByteDance": ["seed", "bytedance", "doubao"], "Apple": ["apple"], "AMD": ["amd"], "HuggingFace": ["smol", "huggingface"],
    "Liquid": ["lfm", "liquid"], "StepFun": ["step", "stepfun"], "Baidu": ["ernie", "baidu"], "Cohere": ["cohere", "command-r"],
}
