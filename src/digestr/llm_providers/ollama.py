#!/usr/bin/env python3
"""
Digestr Ollama LLM Provider
Handles local Ollama integration with multi-model support
"""

import asyncio
import requests
import json
import time
from datetime import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def generate_summary(self, prompt: str, model: str = None) -> str:
        """Generate a summary response"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        pass
    
    @abstractmethod
    def create_summary_prompt(self, articles: List[Dict], briefing_type: str = "comprehensive") -> str:
        """Create a summary prompt from articles"""
        pass


class OllamaProvider(LLMProvider):
    """Ollama local LLM provider with enhanced prompt engineering"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434", models: Dict[str, str] = None):
        self.ollama_url = ollama_url.rstrip('/')
        self.models = models or {
            "default": "llama3.1:8b",
            "technical": "deepseek-r1:14b",
            "conversational": "llama3.1:8b",
            "academic": "qwen2.5:14b",
            "fast": "llama3.1:8b",
            "detailed": "qwen2.5:14b"
        }
        self._available_models_cache = None
        self._cache_timestamp = 0
    
    async def generate_summary(self, prompt: str, model: str = None) -> str:
        if model is None:
            model = self.models["default"]
        
        try:
            # Use ThreadPoolExecutor for blocking requests call
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                response = await loop.run_in_executor(
                    executor,
                    lambda: requests.post(
                        f"{self.ollama_url}/api/generate",
                        json={
                            "model": model,
                            "prompt": prompt,
                            "stream": False,
                            "options": {
                                "temperature": 0.7,
                                "top_p": 0.9,
                                "num_ctx": 4096,
                                "stop": ["Human:", "Assistant:", "\n\nHuman:", "\n\nAssistant:"]
                            }
                        },
                        timeout=120
                    )
                )
            
            response.raise_for_status()
            result = response.json()
            
            if "response" in result:
                return result["response"].strip()
            else:
                logger.error(f"Unexpected Ollama response format: {result}")
                return "Error: Unexpected response format from Ollama"
                
        except requests.exceptions.ConnectionError:
            error_msg = f"Cannot connect to Ollama at {self.ollama_url}. Is Ollama running?"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except requests.exceptions.Timeout:
            error_msg = "Ollama request timed out after 120 seconds"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except requests.exceptions.RequestException as e:
            error_msg = f"Ollama API error: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Unexpected error calling Ollama: {e}"
            logger.error(error_msg)
            return f"Error: {error_msg}"
    
    def validate_config(self) -> bool:
        """Validate Ollama configuration and connectivity"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.warning(f"Ollama validation failed: {e}")
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models with caching"""
        current_time = time.time()
        
        # Use cache if it's less than 5 minutes old
        if (self._available_models_cache is not None and 
            current_time - self._cache_timestamp < 300):
            return self._available_models_cache
        
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=10)
            response.raise_for_status()
            
            models_data = response.json()
            available_models = [model["name"] for model in models_data.get("models", [])]
            
            # Update cache
            self._available_models_cache = available_models
            self._cache_timestamp = current_time
            
            return available_models
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Could not fetch available models: {e}")
            # Return configured models as fallback
            return list(self.models.values())
    
    def create_summary_prompt(self, articles: List[Dict], briefing_type: str = "comprehensive") -> str:
        """Create an enhanced summary prompt optimized for Ollama models"""
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Group articles by category for better organization
        categorized = {}
        for article in articles:
            cat = article['category']
            if cat not in categorized:
                categorized[cat] = []
            categorized[cat].append(article)
        
        # Build article content with importance indicators
        article_text = ""
        total_articles = len(articles)
        
        for category, cat_articles in categorized.items():
            article_text += f"\n## {category.upper().replace('_', ' ')} ({len(cat_articles)} articles)\n"
            
            # Sort by importance score
            cat_articles.sort(key=lambda x: x.get('importance_score', 0), reverse=True)
            
            for i, article in enumerate(cat_articles, 1):
                importance = article.get('importance_score', 0)
                if importance > 5:
                    indicator = "🔥 HIGH IMPACT"
                elif importance > 2:
                    indicator = "📌 NOTABLE"
                else:
                    indicator = "📄"
                
                article_text += f"\n{indicator} **{article['title']}**\n"
                article_text += f"Source: {article.get('source', 'Unknown')}\n"
                
                # Use content if available, otherwise summary
                content = article.get('content') or article.get('summary', '')
                if len(content) > 400:
                    content = content[:400] + "..."
                
                article_text += f"{content}\n"
                if i < len(cat_articles):
                    article_text += "---\n"
        


    async def generate_tiered_briefing(self, tiered_articles: Dict[str, List[Dict]], 
                                     briefing_type: str = "comprehensive") -> str:
        """
        Generate a briefing using strategically tiered articles
        """
        if not any(tiered_articles.values()):
            return "No articles available for briefing."
        
        # Create tiered prompt
        prompt = self._create_tiered_prompt(tiered_articles, briefing_type)
        
        # Use the conversational model for better flow
        model = self.models.get("conversational", self.models["default"])
        
        logger.info(f"Generating tiered {briefing_type} briefing with {model}")
        
        # Generate the briefing
        briefing = await self.generate_summary(prompt, model)
        
        # Post-process to ensure links
        from digestr.core.link_processor import LinkProcessor
        processor = LinkProcessor()
        
        # Collect all articles
        all_articles = []
        for tier_articles in tiered_articles.values():
            all_articles.extend(tier_articles)
        
        # Process briefing to add missing links
        briefing = processor.process_briefing_content(briefing, all_articles)
        
        return briefing
    
    def _create_tiered_prompt(self, tiered_articles: Dict[str, List[Dict]], 
                            briefing_type: str = "comprehensive") -> str:
        """
        Create a conversational prompt that handles tiered content strategically
        """
        current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
        
        # Count articles and sources
        top_count = len(tiered_articles.get('top', []))
        mid_count = len(tiered_articles.get('mid', []))
        quick_count = len(tiered_articles.get('quick', []))
        total_count = top_count + mid_count + quick_count
        
        # Build content sections
        content_sections = self._build_content_sections(tiered_articles)
        
        # Conversational style configurations
        style_configs = {
            "comprehensive": {
                "greeting": "Good afternoon! I've been following the news and have quite a bit to catch you up on.",
                "approach": "Let's dive deep into what's really happening and why it matters.",
                "tone": "conversational but thorough"
            },
            "quick": {
                "greeting": "Hey there! Quick update on what's making headlines.",
                "approach": "I'll hit the highlights and key developments you should know about.",
                "tone": "brisk and efficient"
            },
            "analytical": {
                "greeting": "I've been analyzing today's developments and there are some interesting patterns emerging.",
                "approach": "Let me walk you through the implications and connections I'm seeing.",
                "tone": "thoughtful and insight-focused"
            }
        }
        
        style = style_configs.get(briefing_type, style_configs["comprehensive"])
        
        # Create the enhanced conversational prompt
        prompt = f"""You are my trusted news analyst and friend. It's {current_time}, and I'm catching up on what's been happening. {style['greeting']}

I've analyzed {total_count} articles from various sources and organized them by importance. {style['approach']}

{content_sections}

CONVERSATIONAL BRIEFING STYLE:
- Tone: {style['tone']}
- Flow: Natural conversation, not bullet points or formal sections
- Connection: Weave related stories together naturally
- Context: Explain why things matter, don't just report what happened
- Engagement: Keep it interesting and insightful

BRIEFING STRUCTURE:
1. Start with a warm, natural greeting that acknowledges the current time
2. Lead with the most significant developments from the TOP PRIORITY stories
3. Naturally flow into the NOTABLE DEVELOPMENTS, connecting related themes
4. Weave in QUICK MENTIONS of other interesting stories where relevant
5. Throughout, explain connections between stories and their broader significance
6. End with brief thoughtful insight about what these developments mean going forward

IMPORTANT GUIDELINES:
- Write in flowing paragraphs, not bullet points
- Connect stories across categories when they relate
- Use phrases like "Speaking of..." "This connects to..." "What's particularly interesting is..."
- Include specific details and examples to make it engaging
- Explain implications and why readers should care
- Maintain a conversational, friendly tone throughout
- Naturally mention source variety when relevant

Begin your conversational briefing now:"""

        return prompt
    
    def _build_content_sections(self, tiered_articles: Dict[str, List[Dict]]) -> str:
        """
        Build organized content sections for the prompt
        """
        sections = []
        
        # Top Priority Stories (detailed treatment)
        top_articles = tiered_articles.get('top', [])
        if top_articles:
            sections.append("TOP PRIORITY STORIES (for detailed discussion):")
            for i, article in enumerate(top_articles[:15], 1):  # Limit to avoid overwhelming
                score = article.get('calculated_priority_score', 0)
                sections.append(f"\n{i}. **{article['title']}**")
                sections.append(f"   Source: {article.get('source', 'Unknown')} | Priority Score: {score:.1f}")
                
                # Use content if available, otherwise summary
                content = article.get('content') or article.get('summary', '')
                if len(content) > 400:
                    content = content[:400] + "..."
                sections.append(f"   {content}")
                
                # Add category context
                category = article.get('category', 'unknown')
                sections.append(f"   Category: {category}")
        
        # Notable Developments (moderate treatment)
        mid_articles = tiered_articles.get('mid', [])
        if mid_articles:
            sections.append(f"\n\nNOTABLE DEVELOPMENTS (for moderate coverage):")
            for i, article in enumerate(mid_articles[:20], 1):  # Limit for brevity
                score = article.get('calculated_priority_score', 0)
                sections.append(f"\n{i}. **{article['title']}** ({article.get('source', 'Unknown')})")
                
                # Shorter content for mid-tier
                content = article.get('content') or article.get('summary', '')
                if len(content) > 200:
                    content = content[:200] + "..."
                sections.append(f"   {content}")
        
        # Quick Mentions (brief treatment)
        quick_articles = tiered_articles.get('quick', [])
        if quick_articles:
            sections.append(f"\n\nQUICK MENTIONS (brief notes on other stories):")
            
            # Group quick mentions by category for better organization
            quick_by_category = {}
            for article in quick_articles[:25]:  # Limit to top 25 quick mentions
                category = article.get('category', 'other')
                if category not in quick_by_category:
                    quick_by_category[category] = []
                quick_by_category[category].append(article)
            
            for category, cat_articles in quick_by_category.items():
                sections.append(f"\n{category.upper().replace('_', ' ')}:")
                for article in cat_articles[:8]:  # Max 8 per category
                    sections.append(f"• {article['title']} ({article.get('source', 'Unknown')})")
        
        return "\n".join(sections)
    
    def _extract_key_themes(self, tiered_articles: Dict[str, List[Dict]]) -> List[str]:
        """
        Extract key themes across all articles for better narrative flow
        """
        themes = []
        
        # Analyze top articles for major themes
        top_articles = tiered_articles.get('top', [])
        
        # Simple keyword-based theme detection
        theme_keywords = {
            'technology': ['ai', 'artificial intelligence', 'tech', 'innovation', 'digital'],
            'geopolitics': ['ukraine', 'russia', 'china', 'election', 'politics', 'government'],
            'economy': ['market', 'economy', 'business', 'financial', 'trade', 'stocks'],
            'security': ['cyber', 'security', 'hack', 'attack', 'breach', 'threat'],
            'health': ['health', 'medical', 'vaccine', 'disease', 'pandemic'],
            'climate': ['climate', 'environment', 'renewable', 'sustainability', 'carbon']
        }
        
        theme_counts = {theme: 0 for theme in theme_keywords.keys()}
        
        for article in top_articles:
            title_lower = article.get('title', '').lower()
            content_lower = (article.get('content', '') or article.get('summary', '')).lower()
            full_text = f"{title_lower} {content_lower}"
            
            for theme, keywords in theme_keywords.items():
                if any(keyword in full_text for keyword in keywords):
                    theme_counts[theme] += 1
        
        # Return themes with significant presence
        significant_themes = [theme for theme, count in theme_counts.items() if count >= 2]
        
        return significant_themes[:5]



        # Briefing style configurations
        style_configs = {
            "comprehensive": {
                "instruction": "Provide a thorough, insightful briefing that connects related stories and offers context.",
                "tone": "professional yet conversational",
                "focus": "comprehensive analysis with connections between stories"
            },
            "quick": {
                "instruction": "Give a concise, punchy summary hitting only the most important points.",
                "tone": "direct and efficient",
                "focus": "key headlines and critical developments only"
            },
            "analytical": {
                "instruction": "Focus on implications, underlying trends, and deeper meaning.",
                "tone": "analytical and thoughtful",
                "focus": "strategic insights and trend analysis"
            },
            "casual": {
                "instruction": "Present the news in a friendly, conversational way.",
                "tone": "warm and approachable",
                "focus": "accessible explanations with personal relevance"
            }
        }
        
        style_config = style_configs.get(briefing_type, style_configs["comprehensive"])
        
        # Create the optimized prompt
        prompt = f"""You are an expert news analyst providing a personalized briefing. Current time: {current_time}

ARTICLES TO ANALYZE ({total_articles} total):
{article_text}

BRIEFING REQUIREMENTS:
Style: {briefing_type.title()}
Instruction: {style_config['instruction']}
Tone: {style_config['tone']}
Focus: {style_config['focus']}

STRUCTURE YOUR RESPONSE:
1. Start with a natural greeting that acknowledges the current time
2. Highlight the most significant developments first
3. Group related stories and explain connections
4. Provide context for why stories matter
5. End with a thoughtful summary that ties key themes together

GUIDELINES:
- Be engaging and insightful, not just informative
- Connect stories across categories when relevant
- Explain implications and significance
- Use clear, accessible language
- Include specific details and examples
- Maintain the specified tone throughout

Begin your briefing:"""

        return prompt
    
    async def generate_briefing(self, articles: List[Dict], briefing_type: str = "comprehensive", 
                              model: str = None) -> str:
        """Generate a complete briefing with timing and error handling"""
        start_time = time.time()
        
        if not articles:
            return "No articles available for briefing."
        
        # Select appropriate model based on briefing type
        if model is None:
            model_mapping = {
                "quick": self.models["fast"],
                "technical": self.models["technical"],
                "analytical": self.models["detailed"],
                "academic": self.models["academic"],
                "comprehensive": self.models["default"]
            }
            model = model_mapping.get(briefing_type, self.models["default"])
        
        # Create optimized prompt
        prompt = self.create_summary_prompt(articles, briefing_type)
        
        # Generate summary
        logger.info(f"Generating {briefing_type} briefing with model {model} for {len(articles)} articles")
        summary = await self.generate_summary(prompt, model)
        
        processing_time = time.time() - start_time
        logger.info(f"Briefing generated in {processing_time:.2f} seconds")
        
        return summary
    
    def get_model_for_category(self, category: str) -> str:
        """Get the most appropriate model for a specific category"""
        category_model_mapping = {
            "tech": self.models["technical"],
            "cutting_edge": self.models["academic"],
            "security": self.models["technical"],
            "business": self.models["detailed"],
            "world_news": self.models["conversational"],
            "sports": self.models["fast"]
        }
        
        return category_model_mapping.get(category, self.models["default"])
    
    async def test_model_performance(self, model: str) -> Dict[str, any]:
        """Test a specific model's performance and capabilities"""
        test_prompt = "Summarize this in one sentence: The latest developments in artificial intelligence show promising results."
        
        start_time = time.time()
        
        try:
            response = await self.generate_summary(test_prompt, model)
            response_time = time.time() - start_time
            
            return {
                "model": model,
                "success": True,
                "response_time": response_time,
                "response_length": len(response),
                "response_quality": "good" if len(response) > 10 else "poor"
            }
        except Exception as e:
            return {
                "model": model,
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time
            }
    
    async def benchmark_all_models(self) -> Dict[str, Dict[str, any]]:
        """Benchmark all configured models"""
        results = {}
        
        for model_type, model_name in self.models.items():
            logger.info(f"Benchmarking {model_type} model: {model_name}")
            results[model_type] = await self.test_model_performance(model_name)
        
        return results
    
    def get_status(self) -> Dict[str, any]:
        """Get detailed status of Ollama provider"""
        return {
            "provider": "ollama",
            "url": self.ollama_url,
            "configured_models": self.models,
            "available_models": self.get_available_models(),
            "connection_valid": self.validate_config()
        }
