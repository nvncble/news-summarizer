# Installation Guide

## 📋 Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Memory**: 4GB RAM minimum, 8GB recommended
- **Storage**: 1GB free space

### Required Software
- **[Ollama](https://ollama.ai)**: For local LLM processing
- **Git**: For cloning the repository

## 🚀 Quick Installation

### 1. Install Ollama
```bash
# macOS
brew install ollama

# Linux
curl -fsSL https://ollama.ai/install.sh | sh

# Windows: Download from https://ollama.ai/download



2. Pull Required Models
# Install recommended models
ollama pull llama3.1:8b          # Default model
ollama pull deepseek-coder:6.7b  # Technical content
3. Clone and Setup Digestr
# Clone repository
git clone https://github.com/nvncble/news-summarizer.git
cd news-summarizer

# Install dependencies
pip install -r requirements.txt

# Verify installation
python digestr_cli_enhanced.py status
🧪 Verification
Test Installation
# Check system status
python digestr_cli_enhanced.py status

# Expected output:
# 🔍 Digestr.ai System Status
# ✅ Version: 2.0.0
# ✅ Database: Ready
# ✅ Ollama: Ready
# 🎯 Ready for news intelligence!
Test Functionality
# Test new CLI
python digestr_cli_enhanced.py fetch
python digestr_cli_enhanced.py articles

# Test legacy compatibility
python src/rss_summarizer.py
🔧 Troubleshooting
Common Issues
"Cannot connect to Ollama"
# Check Ollama is running
ollama list

# Start Ollama if needed
ollama serve
"ModuleNotFoundError: No module named 'yaml'"
# Install missing dependency
pip install pyyaml
