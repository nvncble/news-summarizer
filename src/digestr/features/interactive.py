#!/usr/bin/env python3
"""
Digestr Interactive Session Module
Provides conversation-based news analysis and follow-up capabilities
"""

import asyncio
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class InteractiveSession:
    """
    Interactive conversation session for news analysis
    Enables follow-up questions and contextual discussions about news articles
    """

    def __init__(self, articles: List[Dict], llm_provider):
        self.articles = articles
        self.llm_provider = llm_provider
        self.conversation_history = []
        self.session_context = self._build_session_context()
        self.max_context_length = 4000  # Token limit for context

    def _build_session_context(self) -> str:
        """Build context summary from articles for the session"""
        if not self.articles:
            return "No articles available for discussion."
        
        # Group articles by category for better context
        categories = {}
        for article in self.articles:
            cat = article.get('category', 'general')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(article)
        
        context_parts = []
        context_parts.append(f"CURRENT NEWS CONTEXT ({len(self.articles)} articles available):\n")
        
        for category, cat_articles in categories.items():
            context_parts.append(f"\n{category.upper()} ({len(cat_articles)} articles):")
            
            # Sort by importance
            sorted_articles = sorted(cat_articles, 
                                key=lambda x: x.get('importance_score', 0), 
                                reverse=True)
            
            # Include ALL articles, but with varying detail levels
            for i, article in enumerate(sorted_articles):
                importance = article.get('importance_score', 0)
                
                # Always include title
                context_parts.append(f"\n{i+1}. {article['title']}")
                context_parts.append(f"   Source: {article.get('source', 'Unknown')} | Published: {article.get('published_date', 'Unknown')}")
                
                # For top 5 articles OR if importance > 3, include content preview
                if i < 5 or importance > 3:
                    content = article.get('content') or article.get('summary', '')
                    if content:
                        brief_content = content[:200] + "..." if len(content) > 200 else content
                        context_parts.append(f"   {brief_content}")
        
        return "\n".join(context_parts)

    async def start(self):
        """Start the interactive session"""
        print("🎯 Interactive Session Started")
        print("📚 I have context from your recent news articles")
        print("💬 Ask me anything about the news, or type 'exit' to quit")
        print("💡 Try: 'Tell me more about...', 'How does this relate to...', 'What's the significance of...'")
        print("-" * 60)

        while True:
            try:
                # Get user input
                user_input = input("\n🤔 Your question: ").strip()

                if not user_input:
                    continue

                # Check for exit commands
                if user_input.lower() in ['exit', 'quit', 'bye', 'done']:
                    print("👋 Thanks for the conversation! Session ended.")
                    break

                # Check for help commands
                if user_input.lower() in ['help', '?']:
                    self._show_help()
                    continue

                # Check for special commands
                if user_input.lower().startswith('/'):
                    await self._handle_special_command(user_input)
                    continue

                # Process the question
                print("🤖 Analyzing...")
                response = await self._process_question(user_input)
                print(f"\n💡 {response}\n")

            except KeyboardInterrupt:
                print("\n👋 Session interrupted. Goodbye!")
                break
            except Exception as e:
                logger.error(f"Error in interactive session: {e}")
                print(f"❌ Sorry, I encountered an error: {e}")
                print("💡 Try rephrasing your question or type 'help' for assistance")

    async def _process_question(self, question: str) -> str:
        """Process a user question and generate a contextual response"""
        # Build the conversation prompt
        prompt = self._create_conversation_prompt(question)

        # Generate response using LLM
        # Use the conversational model if available
        model = self.llm_provider.models.get(
            "conversational", self.llm_provider.models["default"])

        try:
            # Note: generate_summary works but isn't ideal for conversations
            # We're using it for now since it's what's available
            response = await self.llm_provider.generate_summary(prompt, model=model)

            # Update conversation history
            self.conversation_history.append({
                'question': question,
                'response': response
            })

            # Trim history if it gets too long
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-8:]

            return response

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I apologize, but I encountered an error processing your question. Could you try rephrasing it?"

    def _create_conversation_prompt(self, question: str) -> str:
        """Create a conversation prompt with context and history"""
        
        # Build conversation history context
        history_context = ""
        if self.conversation_history:
            history_context = "\nPREVIOUS CONVERSATION:\n"
            for i, exchange in enumerate(self.conversation_history[-3:], 1):  # Last 3 exchanges
                history_context += f"Q{i}: {exchange['question']}\n"
                history_context += f"A{i}: {exchange['response'][:100]}...\n"
        
        prompt = f"""You are an intelligent news analyst assistant. You're having a conversation with a user about recent news articles.

    {self.session_context}

    {history_context}

    CURRENT QUESTION: {question}

    INSTRUCTIONS:
    - For questions about CURRENT NEWS: Only reference the articles provided above
    - For questions about HISTORICAL CONTEXT or GENERAL KNOWLEDGE: You may use your broader knowledge
    - Be clear about the distinction: "While I don't have current articles about X, historically..."
    - NEVER fabricate current events, recent dates, or claim things happened recently if not in the articles
    - NEVER invent specific claims about real people that aren't in the provided articles
    - When providing historical context, use phrases like "historically," "in the past," "generally speaking"
    - If asked about current events not in the articles, say: "I don't have any current articles about that"
    - Connect historical knowledge to current articles when relevant
    - Keep responses concise but informative (2-3 paragraphs max)

    Examples of good responses:
    - "I don't have current articles about Trump's Nobel nomination, but historically, Nobel Prize controversies have included..."
    - "While none of today's articles cover this topic, past examples of similar situations include..."

    RESPONSE:"""

        return prompt

    def _show_help(self):
        """Show help information for the interactive session"""
        print("\n📚 Interactive Session Help:")
        print("\n🔍 What you can ask:")
        print("  • 'Tell me more about [topic/company/event]'")
        print("  • 'How does this relate to [other topic]?'")
        print("  • 'What's the significance of [news item]?'")
        print("  • 'Summarize the [category] news'")
        print("  • 'What are the implications of [event]?'")

        print("\n⚡ Special commands:")
        print("  • /articles - List available articles")
        print("  • /categories - Show news categories")
        print("  • /recent - Show most recent articles")
        print("  • /important - Show highest importance articles")

        print("\n🚪 To exit:")
        print("  • Type 'exit', 'quit', 'bye', or 'done'")
        print("  • Press Ctrl+C")

        print("\n⚡ Special commands:")
        print("  • /articles - List available articles")
        print("  • /categories - Show news categories")
        print("  • /recent - Show most recent articles")
        print("  • /important - Show highest importance articles")
        print("  • /read [number] - Read full content of an article")

    async def _handle_special_command(self, command: str):
        """Handle special slash commands"""
        command = command.lower().strip()
        
        if command == '/articles':
            self._list_articles()
        elif command == '/categories':
            self._show_categories()
        elif command == '/recent':
            self._show_recent_articles()
        elif command == '/important':
            self._show_important_articles()
        elif command.startswith('/read '):
            article_num = command[6:]  # Remove '/read '
            self._read_article(article_num)
        else:
            print(f"❌ Unknown command: {command}")
            print("💡 Type 'help' to see available commands")
        def _list_articles(self):
            """List all available articles"""
            print(f"\n📰 Available Articles ({len(self.articles)} total):")

        for i, article in enumerate(self.articles[:10], 1):  # Show first 10
            importance = article.get('importance_score', 0)
            indicator = "🔥" if importance > 5 else "📌" if importance > 2 else "📄"

            print(f"  {i:2d}. {indicator} {article['title'][:60]}...")
            print(
                f"      Source: {article.get('source', 'Unknown')} | Category: {article.get('category', 'Unknown')}")

        if len(self.articles) > 10:
            print(f"      ... and {len(self.articles) - 10} more articles")

    def _show_categories(self):
        """Show articles grouped by categories"""
        categories = {}
        for article in self.articles:
            cat = article.get('category', 'Unknown')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(article)

        print(f"\n📂 Articles by Category:")
        for category, cat_articles in sorted(categories.items()):
            avg_importance = sum(a.get('importance_score', 0)
                                 for a in cat_articles) / len(cat_articles)
            print(
                f"  📁 {category}: {len(cat_articles)} articles (avg importance: {avg_importance:.1f})")

    def _show_recent_articles(self):
        """Show most recently published articles"""
        # Sort by published date if available, otherwise by fetched date
        sorted_articles = sorted(
            self.articles,
            key=lambda x: x.get('published_date', ''),
            reverse=True
        )

        print(f"\n⏰ Most Recent Articles:")
        for i, article in enumerate(sorted_articles[:5], 1):
            print(f"  {i}. {article['title'][:60]}...")
            print(
                f"     {article.get('source', 'Unknown')} | {article.get('published_date', 'Unknown date')}")

    def _show_important_articles(self):
        """Show highest importance articles"""
        sorted_articles = sorted(
            self.articles,
            key=lambda x: x.get('importance_score', 0),
            reverse=True
        )


    def _read_article(self, article_number: str):
        """Read the full content of a specific article"""
        try:
            num = int(article_number) - 1  # Convert to 0-based index
            if 0 <= num < len(self.articles):
                article = self.articles[num]
                print(f"\n📄 Full Article #{article_number}:")
                print(f"Title: {article['title']}")
                print(f"Source: {article.get('source', 'Unknown')}")
                print(f"Published: {article.get('published_date', 'Unknown')}")
                print(f"Category: {article.get('category', 'Unknown')}")
                print(f"Importance: {article.get('importance_score', 0):.1f}")
                print("\nContent:")
                content = article.get('content') or article.get('summary', 'No content available')
                print(content)
            else:
                print(f"❌ Invalid article number. Please use 1-{len(self.articles)}")
        except ValueError:
            print("❌ Please provide a valid article number")


        print(f"\n🔥 Highest Importance Articles:")
        for i, article in enumerate(sorted_articles[:5], 1):
            importance = article.get('importance_score', 0)
            print(f"  {i}. [{importance:.1f}] {article['title'][:55]}...")
            print(
                f"     {article.get('source', 'Unknown')} | {article.get('category', 'Unknown')}")

    def get_session_summary(self) -> Dict[str, any]:
        """Get a summary of the session"""
        return {
            'articles_count': len(self.articles),
            'questions_asked': len(self.conversation_history),
            'categories_available': len(set(a.get('category', 'Unknown') for a in self.articles)),
            'conversation_length': len(self.conversation_history)
        }
        # Update conversation history
        self.conversation_history.append
