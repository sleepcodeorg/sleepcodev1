# Providers Guide

SleepCode uses [LiteLLM](https://github.com/BerriAI/litellm) under the hood to support bring-your-own-key (BYOK) for various LLM providers.

## Supported Model Formats
- **OpenAI**: `openai/gpt-4o`, `openai/gpt-4o-mini`
- **Anthropic**: `anthropic/claude-3-5-sonnet-20241022`
- **Groq**: `groq/llama-3.3-70b-versatile`
- **Google Gemini**: `gemini/gemini-1.5-pro`
- **OpenRouter**: `openrouter/anthropic/claude-3.5-sonnet`
- **Mistral**: `mistral/mistral-large-latest`
- **Ollama**: `ollama/llama3` (Requires Ollama running locally at `http://localhost:11434`, no API key needed)

## Configuring API Keys
Keys can be set via environment variables:
```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GROQ_API_KEY="gsk_..."
export GEMINI_API_KEY="AIza..."
```
Or stored securely in `~/.sleepcode/config.yaml`:
```bash
sleepcode config set-key openai
```
