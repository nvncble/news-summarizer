# Contributing to Digestr.ai

Welcome! We're excited about your interest in contributing to Digestr.ai.

## 🚀 Quick Start for Contributors

### Development Setup
```bash
# Fork and clone
git clone https://github.com/nvncble/news-summarizer.git
cd news-summarizer

# Install dependencies
pip install -r requirements.txt

# Verify setup
python digestr_cli_enhanced.py status
Running Tests
bash# Test that modules work
python test_api.py

# Test CLI functionality
python digestr_cli_enhanced.py --help
python digestr_cli_enhanced.py status
🎯 Areas for Contribution
🔧 Core Improvements

Performance optimization: Database queries, RSS fetching
Error handling: Edge cases, network failures
Documentation: Code comments, examples
Testing: Unit tests, integration tests

✨ New Features

Interactive Mode: Conversation-based follow-ups
LLM Providers: OpenAI, Anthropic, local models
Feed Sources: New RSS feeds, content sources
Export Formats: PDF, email, mobile apps

🌐 Community Features

Feed Collections: Curated RSS bundles
Prompt Templates: Specialized briefing styles
Integration: Slack, Discord, webhooks

📋 Development Guidelines
Code Style

Python: Follow PEP 8
Type Hints: Required for new code
Documentation: Docstrings for all public methods
Error Handling: Graceful degradation with logging

Architecture Principles

Modularity: Single responsibility, clean interfaces
Backward Compatibility: Preserve existing APIs
Configuration: Feature flags for new capabilities
Testing: Test all new functionality

Git Workflow
bash# Create feature branch
git checkout -b feature/your-feature-name

# Make changes with clear commits
git commit -m "feat: add your feature description"

# Submit pull request with description
Commit Message Format
feat(cli): add interactive briefing mode
fix(database): resolve connection pool leak
docs(api): update configuration examples
test(fetcher): add RSS parsing edge cases
🧪 Testing Guidelines
Manual Testing
bash# Test core functionality
python digestr_cli_enhanced.py status
python digestr_cli_enhanced.py fetch
python digestr_cli_enhanced.py briefing

# Test legacy compatibility
python src/rss_summarizer.py
🐛 Bug Reports
Before Reporting

Check existing issues for duplicates
Test with latest version
Reproduce with minimal example

Bug Report Template
markdown**Environment:**
- OS: Windows 10 / macOS 12 / Ubuntu 20.04
- Python: 3.9.5
- Digestr: 2.0.0

**Description:**
Clear description of the bug

**Steps to Reproduce:**
1. Run `python digestr_cli_enhanced.py status`
2. Execute `python digestr_cli_enhanced.py fetch`
3. Error occurs

**Expected vs Actual Behavior:**
What should happen vs what actually happens
📄 License
By contributing, you agree that your contributions will be licensed under the MIT License.

Thank you for helping make Digestr.ai better! 🚀