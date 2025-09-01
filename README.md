# 🧠 L13-applet dev

Automaton13 DSVM stack with multi-agent LLM integration and fractal mathematics.

## 🚀 Quick Start

```bash
git clone -b dev https://github.com/nhartman000/L13-applet.git
cd L13-applet
cp .env.example .env
# Configure GPT_BEARER in .env
docker compose up -d --build
```

## 📚 Documentation

- [🎭 Emoji Lexicon](docs/emoji-lexicon.md) - System emoji threading patterns
- [🔬 Mathematics](docs/mathematics.md) - Auto13 algorithm parameters and functions

## 🏗️ Architecture

- **Kernel Service** (Port 8000) - Auto13 algorithm with applet fan-out
- **Applet Service** (Port 9001) - LLM integration with retry logic  
- **PWA Frontend** - Progressive web app interface
- **Caddy Proxy** - Reverse proxy and static file serving
