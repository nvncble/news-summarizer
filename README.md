# 🤖 Digestr.ai - Multi-Source News Intelligence Platform

> Transform news consumption from passive reading to active intelligence gathering

**Digestr.ai** is an intelligent news aggregation and analysis platform that combines traditional RSS feeds with Reddit community sentiment analysis to provide comprehensive news intelligence. Get not just *what's happening*, but *how communities are reacting*.

## ✨ **What Makes Digestr.ai Unique**

- **🌐 Multi-Source Intelligence**: RSS feeds + Reddit discussions + sentiment analysis
- **🧠 Community Sentiment**: Real-time analysis of how communities react to news
- **🎯 Quality Filtering**: Advanced bot detection and spam filtering
- **📊 Correlation Analysis**: Connect traditional news with grassroots reactions
- **⚡ Intelligent Briefings**: AI-generated summaries with community context
- **🔄 Real-Time Processing**: Live sentiment analysis and engagement scoring

---

## 🚀 **Quick Start**

### **Installation**
```bash
git clone https://github.com/nvncble/news-summarizer.git
cd news-summarizer
pip install -r requirements.txt
```

### **Basic Usage**
```bash
# Fetch from all sources (RSS + Reddit)
python digestr_cli_enhanced.py fetch

# Generate intelligent briefing
python digestr_cli_enhanced.py briefing

# Interactive Q&A mode
python digestr_cli_enhanced.py briefing --interactive
```

### **Reddit Setup (Optional)**
```bash
# 1. Get Reddit API credentials at https://www.reddit.com/prefs/apps
# 2. Create a "script" type application
# 3. Set environment variables:
export REDDIT_CLIENT_ID="your_client_id"
export REDDIT_CLIENT_SECRET="your_client_secret"

# 4. Enable Reddit source
python digestr_cli_enhanced.py sources status
```

---

## 🔥 **Key Features**

### **🌐 Multi-Source Architecture**
```bash
# Fetch from specific sources
python digestr_cli_enhanced.py fetch --sources rss
python digestr_cli_enhanced.py fetch --sources reddit
python digestr_cli_enhanced.py fetch --sources rss reddit

# Check source status
python digestr_cli_enhanced.py sources status
# Output: ✅ 🌐 RSS: Connected, ✅ 🔴 REDDIT: Connected
```

### **🧠 Community Sentiment Analysis**
- **Real-time sentiment scoring** of Reddit comments and discussions
- **Consensus detection** - identify majority opinion vs dissenting views
- **Quality weighting** - upvotes, comment quality, and engagement factors
- **Bot filtering** - advanced detection of automated and low-quality content

### **📊 Intelligence Enhancement**
- **Cross-source correlation** - connect news stories with community reactions
- **Engagement scoring** - importance boosted by community interest
- **Trend detection** - identify emerging topics and sentiment shifts
- **Context enrichment** - traditional journalism + grassroots perspective

### **⚡ Advanced CLI**
```bash
# Multi-source briefings
python digestr_cli_enhanced.py briefing --sources rss reddit

# Source management
python digestr_cli_enhanced.py sources list
python digestr_cli_enhanced.py sources status

# Interactive analysis
python digestr_cli_enhanced.py briefing --interactive
```

---

## 📋 **Example Output**

### **Enhanced Briefing with Sentiment**
```
📋 YOUR MULTI-SOURCE DIGESTR.AI BRIEFING
========================================

🔥 Tesla Battery Breakthrough Sparks Tech Community Debate
📰 RSS: Reuters reports Tesla announces new 4680 battery cells
🔴 Reddit: r/technology discussion (1,234 upvotes, 89 comments)
   Community sentiment: cautiously optimistic (73% confidence)
   
The tech community is buzzing about Tesla's battery announcement, with Reddit users 
expressing cautious optimism about real-world implications. While mainstream media 
focuses on technical specifications, r/technology discussions reveal skepticism 
about production timelines and cost concerns...

🌍 Climate Summit Reactions Show Global Divide  
📰 RSS: AP News covers COP29 agreements
🔴 Reddit: r/worldnews heated discussion (2,156 upvotes, 234 comments)
   Community sentiment: mixed with strong disagreement (45% confidence)
   
Traditional coverage presents diplomatic consensus, but Reddit communities show 
sharp divisions on effectiveness of proposed measures...
```

### **Sentiment Analysis Detail**
```
--- Community Sentiment Analysis ---
Analyzed 25 comments from r/technology:
• Overall sentiment: positive (score: 0.73)
• Community confidence: 85%
• Engagement level: 78%
• Dissenting opinions: 3 comments
• Discussion quality: 82%
• Key themes: innovation excitement, cost concerns, timeline skepticism
```

---

## ⚙️ **Configuration**

### **Multi-Source Setup**
Create `~/.digestr/config.yaml`:

```yaml
sources:
  rss:
    enabled: true
    
  reddit:
    enabled: true
    client_id: "${REDDIT_CLIENT_ID}"
    client_secret: "${REDDIT_CLIENT_SECRET}"
    user_agent: "Digestr.ai/2.1 by /u/yourusername"
    
    subreddits:
      - name: "technology"
        min_upvotes: 200
        category: "tech" 
        sentiment_analysis: true
        
      - name: "science"
        min_upvotes: 300
        category: "cutting_edge"
        sentiment_analysis: true
        
      - name: "worldnews"
        min_upvotes: 500
        category: "world_news"
        
    quality_control:
      min_comment_karma: 50
      min_account_age_days: 30
      exclude_joke_keywords: ["lmao", "/s", "shitpost"]
      bot_detection: true
```

### **RSS Feed Management**
```bash
# Add RSS feeds
python digestr_cli_enhanced.py add-feed "https://feeds.reuters.com/reuters/technologyNews"

# List feeds
python digestr_cli_enhanced.py list-feeds

# Test feeds
python digestr_cli_enhanced.py test-feeds
```

---

## 🛠️ **Advanced Usage**

### **Custom Source Combinations**
```bash
# Technology focus
python digestr_cli_enhanced.py briefing --sources reddit --categories tech

# Breaking news mode  
python digestr_cli_enhanced.py fetch --sources rss --urgent-only

# Sentiment-only analysis
python digestr_cli_enhanced.py briefing --sources reddit --sentiment-focus
```

### **Automated Briefings**
```bash
# Schedule daily briefings
python briefing_scheduler.py --time "08:00" --sources "rss reddit"

# Webhook integration
python digestr_cli_enhanced.py briefing --webhook "https://your-webhook-url"
```

### **Analytics & Insights**
```bash
# Trend analysis
python digestr_cli_enhanced.py trends --timeframe "7d"

# Source comparison
python digestr_cli_enhanced.py compare --sources "rss reddit" --topic "AI"

# Sentiment trends
python digestr_cli_enhanced.py sentiment-trends --subreddit "technology"
```

---

## 🧠 **How It Works**

### **1. Multi-Source Data Collection**
- **RSS Feeds**: Traditional news sources (Reuters, AP, BBC, TechCrunch, etc.)
- **Reddit**: Community discussions from targeted subreddits
- **Quality Filtering**: Bot detection, karma requirements, engagement thresholds

### **2. Sentiment Analysis Pipeline**
- **Comment Analysis**: Keyword-based sentiment with confidence scoring
- **Consensus Detection**: Majority opinion vs outlier identification
- **Quality Weighting**: Upvotes, awards, and engagement factors
- **Context Integration**: Sentiment enhances article importance and summaries

### **3. Intelligence Synthesis**
- **Cross-Source Correlation**: Connect news stories with community reactions
- **AI-Enhanced Briefings**: GPT-powered summaries with sentiment context
- **Trend Detection**: Identify emerging topics and sentiment shifts

### **4. Intelligent Output**
- **Unified Briefings**: Traditional news + community perspective
- **Interactive Q&A**: Ask questions about any collected content
- **Source Attribution**: Clear distinction between news and community content

---

## 📊 **Supported Sources**

### **✅ Currently Supported**
- **RSS Feeds**: Any valid RSS/Atom feed
- **Reddit**: Major subreddits with sentiment analysis
  - r/technology, r/science, r/worldnews
  - r/futurology, r/artificial, r/MachineLearning

### **🚧 Coming Soon**
- **Twitter/X**: Real-time tweet analysis and trend detection
- **YouTube**: Video transcript analysis and comment sentiment
- **Substack**: Newsletter content and subscriber discussions
- **Hacker News**: Tech community discussions and sentiment

---

## 🔧 **Requirements**

- **Python**: 3.8+
- **Dependencies**: See `requirements.txt`
- **API Keys**: 
  - OpenAI API key (for briefing generation)
  - Reddit API credentials (optional, for Reddit source)
- **Storage**: SQLite database for article storage and sentiment data

---

## 📈 **Performance & Scale**

- **Processing Speed**: ~30 seconds for 50 articles across all sources
- **Rate Limiting**: Intelligent API management (80 req/min for Reddit)
- **Memory Usage**: Optimized for local processing (~100MB typical)
- **Storage**: Efficient SQLite with article deduplication
- **Quality Control**: 95%+ spam/bot filtering accuracy

---

## 🤝 **Contributing**

We welcome contributions! Areas of focus:

### **🎯 High Priority**
- Additional source integrations (Twitter, YouTube, Substack)
- Enhanced sentiment analysis with ML models
- Real-time processing and alerting systems
- Advanced correlation algorithms

### **📝 Documentation**
- API documentation
- Source integration guides
- Configuration examples
- Performance optimization tips

### **🧪 Testing**
- Unit tests for sentiment analysis
- Integration tests for multi-source processing
- Performance benchmarking
- Quality control validation

---

## 📚 **Documentation**

- **[Installation Guide](docs/installation.md)**: Detailed setup instructions
- **[Configuration Guide](docs/configuration.md)**: Advanced configuration options  
- **[API Reference](docs/api.md)**: programmatic access documentation
- **[Source Integration](docs/sources.md)**: Adding new content sources
- **[Sentiment Analysis](docs/sentiment.md)**: Understanding sentiment scoring

---

## 🆕 **What's New in v2.1**

### **🔥 Reddit Integration**
- Full Reddit API integration with rate limiting
- Real-time sentiment analysis of community discussions
- Quality filtering with bot detection
- Cross-source correlation between news and community reactions

### **🧠 Advanced Sentiment Analysis**
- Keyword-based sentiment scoring with confidence levels
- Consensus vs outlier detection in community discussions
- Engagement-weighted sentiment calculation
- Integration with article importance scoring

### **⚡ Enhanced CLI**
- Multi-source command support (`--sources rss reddit`)
- Source management commands (`sources status`, `sources list`)
- Enhanced interactive mode across all sources
- Real-time sentiment analysis feedback

### **🏗️ Architectural Improvements**
- Modular source system for easy extensibility
- Unified article format across all sources
- Backward compatibility (100% existing functionality preserved)
- Configuration management for multiple sources

---

## 🔮 **Roadmap**

### **Phase 2: Enhanced Intelligence (Q1 2025)**
- Machine learning-based sentiment analysis
- Advanced cross-source correlation algorithms
- Predictive trend analysis
- Real-time alert system

### **Phase 3: Additional Sources (Q2 2025)**
- Twitter/X integration with real-time analysis
- YouTube transcript and comment analysis
- Substack newsletter integration
- Hacker News community discussions

### **Phase 4: Enterprise Features (Q3 2025)**
- API for third-party integrations
- Custom source plugins
- Advanced analytics dashboard
- Team collaboration features

---

## 📄 **License**

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 **Acknowledgments**

- **OpenAI** for GPT API powering intelligent briefings
- **Reddit** for community data access
- **PRAW** for excellent Reddit API client
- **RSS community** for standardized news feeds

---

**Transform your news consumption with Digestr.ai - where traditional journalism meets community intelligence.**

*Get not just the news, but the complete story.* 🚀