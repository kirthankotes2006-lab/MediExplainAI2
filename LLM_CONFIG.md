# LLM API Configuration Guide

## Overview
The Healthcare AI Billing Anomaly Detection System supports multiple LLM providers:
- **OpenAI** (GPT-4o-mini)
- **Google Gemini** (Gemini Pro)
- **Fallback** (Template-based explanations)

The system automatically detects available API keys and uses the best available provider.

## Configuration

### Option 1: OpenAI API

#### Get an API Key:
1. Go to [OpenAI Platform](https://platform.openai.com)
2. Sign up or log in
3. Navigate to **API Keys** section
4. Create a new API key
5. Copy the key (starts with `sk-proj-`)

#### Set the API Key:
```bash
export OPENAI_API_KEY="your-api-key-here"
```

Or add to your shell profile (`~/.zshrc`, `~/.bashrc`):
```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Option 2: Google Gemini API

#### Get an API Key:
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Click "Get API Key"
3. Create a new API key
4. Copy the key

#### Set the API Key:
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

Or add to your shell profile:
```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

### Option 3: Both Providers (Recommended)

For redundancy and automatic failover:
```bash
export OPENAI_API_KEY="your-openai-key"
export GEMINI_API_KEY="your-gemini-key"
```

## Starting the Server

### With OpenAI:
```bash
export OPENAI_API_KEY="sk-proj-..." && \
cd "/Users/kirthankotes/Downloads/healthbilling 2" && \
source venv/bin/activate && \
uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

### With Gemini:
```bash
export GEMINI_API_KEY="..." && \
cd "/Users/kirthankotes/Downloads/healthbilling 2" && \
source venv/bin/activate && \
uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

### With Both (Recommended):
```bash
export OPENAI_API_KEY="sk-proj-..." && \
export GEMINI_API_KEY="..." && \
cd "/Users/kirthankotes/Downloads/healthbilling 2" && \
source venv/bin/activate && \
uvicorn main:app --reload --host 0.0.0.0 --port 8002
```

## Features

### Automatic Provider Selection
The system checks for API keys in this order:
1. OpenAI (if `OPENAI_API_KEY` is set)
2. Gemini (if `GEMINI_API_KEY` is set)
3. Fallback (template-based)

### Automatic Failover
If the preferred provider fails:
- **OpenAI quota exceeded** → Tries Gemini
- **Gemini unavailable** → Falls back to template
- **No API key** → Uses template automatically

### No API Key Exposure
- API keys are stored only as environment variables
- Never exposed to the frontend
- Safely handled on the backend

## Monitoring

Check logs to see which provider is being used:
```
Successfully generated explanation with OpenAI
Successfully generated explanation with Gemini
OpenAI API quota exceeded, trying Gemini
```

## Usage

Once configured, the application will:
1. Generate AI-powered explanations for medical bills
2. Answer patient questions about their bills (with Q&A feature)
3. Automatically fallback if API quota is exceeded
4. Provide template-based explanations if no API is available

## Troubleshooting

### "API quota exceeded" Error
- Switch to a different API provider
- Check your OpenAI/Gemini account billing
- Contact support if still issues

### "API key not configured"
- Verify environment variable is set: `echo $OPENAI_API_KEY`
- Restart the server after setting the key
- Make sure to use `export` not just assignment

### SSL Warning
The `NotOpenSSLWarning` is harmless on macOS with LibreSSL. To suppress:
```bash
export PYTHONWARNINGS="ignore::urllib3.exceptions.NotOpenSSLWarning"
```

## API Limits

### OpenAI (gpt-4o-mini)
- Rate limits vary by plan
- Monitor usage at platform.openai.com

### Gemini (Gemini Pro)
- Free tier: 60 requests/minute
- Paid: Higher limits
- Monitor at aistudio.google.com

## Cost Estimates

### OpenAI GPT-4o-mini
- Input: ~$0.00015 per token
- Output: ~$0.0006 per token
- Typical billing explanation: ~300 tokens (~$0.002)

### Gemini Pro
- Free tier includes monthly usage
- Paid: Competitive pricing
- Check Google's pricing page for current rates
