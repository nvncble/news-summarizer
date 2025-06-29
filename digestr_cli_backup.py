#!/usr/bin/env python3
"""
Digestr CLI - Enhanced command-line interface for news intelligence
Features: interactive mode, configuration management, and community integration
"""
from digestr.features.interactive import InteractiveSession
from digestr.config.manager import get_config_manager, get_config
from digestr.llm_providers.ollama import OllamaProvider
from digestr.core.fetcher import FeedManager, RSSFetcher
from digestr.core.database import DatabaseManager
import logging
from typing import Optional, List
import json
import argparse
import asyncio
import sys

import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


logger = logging.getLogger(__name__)


class DigestrCLI:
    """Main CLI application class"""

    def __init__(self):
        self.config_manager = get_config_manager()
        self.config = get_config()

        # Initialize core components
        self.db_manager = DatabaseManager(self.config.database.path)
        self.feed_manager = FeedManager()
        self.fetcher = RSSFetcher(self.db_manager, self.feed_manager)
        self.llm_provider = OllamaProvider(
            self.config.llm.ollama_url, self.config.llm.models)

    async def run_briefing(self, category: Optional[str] = None, hours: int = 24,
                           style: str = "comprehensive", interactive: bool = False,
                           model: Optional[str] = None, fetch_only: bool = False):
        """Run a news briefing with optional interactive mode"""

        print(f"🚀 Digestr.ai v2.0 - {style.title()} News Briefing")
        print(f"⏰ Analyzing news from the last {hours} hours")
        if category:
            print(f"📂 Category filter: {category}")

        # Fetch latest articles
        print("📡 Fetching latest articles...")

        total_new = sum(category_counts.values())
        if total_new == 0:
            print("📰 No new articles found since last check.")
            if not fetch_only:
                print("💡 Try increasing hours with: --hours 48")
            return

        print(
            f"📈 Found {total_new} new articles across {len(category_counts)} categories")
        if fetch_only:
            self._display_category_summary(category_counts)
            return

        # Get articles for summarization
        articles = self.db_manager.get_recent_articles(
            hours=hours,
            category=category,
            limit=50,
            unprocessed_only=True
        )

        if not articles:
            print("📰 No new articles available for summarization.")
            print("💡 Try: digestr briefing --hours 48")
            return

        # Convert to legacy format for LLM provider
        legacy_articles = [
            {
                'title': article.title,
                'summary': article.summary,
                'content': article.content,
                'url': article.url,
                'category': article.category,
                'source': article.source,
                'published_date': article.published_date,
                'importance_score': article.importance_score
            }
            for article in articles
        ]

        # Generate briefing
        print(f"🤖 Generating {style} briefing...")
        summary = await self.llm_provider.generate_briefing(
            legacy_articles,
            briefing_type=style,
            model=model
        )

        # Display briefing
        self._display_briefing(summary, len(articles), style)

        # Mark articles as processed
        article_urls = [article.url for article in articles]
        self.db_manager.mark_articles_processed(article_urls)

        # Start interactive mode if requested
        if interactive and self.config_manager.is_feature_enabled('interactive_mode'):
            print("\n🎯 Starting interactive mode...")
            print("💡 Ask follow-up questions about the news or type 'exit' to quit")

            session = InteractiveSession(legacy_articles, self.llm_provider)
            await session.start()
        elif interactive:
            print("\n⚠️  Interactive mode is not enabled.")
            print("💡 Enable with: digestr config enable interactive_mode")

    def _display_briefing(self, summary: str, article_count: int, style: str):
        """Display the briefing in a formatted way"""
        print("\n" + "="*80)
        print(
            f"📋 YOUR {style.upper()} NEWS BRIEFING ({article_count} articles)")
        print("="*80)
        print(summary)
        print("\n" + "="*80)

    def _display_category_summary(self, category_counts: dict):
        """Display summary of fetched articles by category"""
        print("\n📊 Articles fetched by category:")
        for category, count in sorted(category_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   {category}: {count} articles")

    async def show_status(self):
        """Display comprehensive system status"""
        print("🔍 Digestr.ai System Status\n")

        # Configuration status
        status = self.config_manager.get_status_summary()
        print("⚙️  Configuration:")
        print(f"   Config file: {status['config_file']}")
        print(f"   Features enabled: {status['features']['total_enabled']}")
        print(f"   LLM provider: {status['llm']['default_provider']}")
        print(
            f"   Database: {'✅' if status['database']['exists'] else '❌'} {status['database']['path']}")

        # Feature status
        features = self.config_manager.list_features()
        enabled_features = [name for name,
                            enabled in features.items() if enabled]
        print(f"\n🎛️  Features ({len(enabled_features)} enabled):")
        for name, enabled in features.items():
            icon = "✅" if enabled else "❌"
            print(f"   {icon} {name}")

        # LLM provider status
        provider_status = self.llm_provider.get_status()
        print(f"\n🤖 LLM Provider ({provider_status['provider']}):")
        print(
            f"   Connection: {'✅' if provider_status['connection_valid'] else '❌'} {provider_status['url']}")
        print(
            f"   Available models: {len(provider_status['available_models'])}")

        # Database statistics
        stats = self.db_manager.get_feed_statistics()
        print(f"\n📊 Database Statistics:")
        print(
            f"   Total articles (7 days): {stats['summary']['total_articles']}")
        print(f"   Active categories: {stats['summary']['active_categories']}")

        if stats['categories']:
            print("   Top categories:")
            for cat, info in list(stats['categories'].items())[:3]:
                print(
                    f"     {cat}: {info['count']} articles, {info['processing_rate']}% processed")

    def manage_config(self, action: str, feature: Optional[str] = None, value: Optional[str] = None):
        """Handle configuration management commands"""
        if action == "show":
            self._show_config()
        elif action == "enable" and feature:
            if self.config_manager.enable_feature(feature):
                print(f"✅ Enabled feature: {feature}")
            else:
                print(f"❌ Unknown feature: {feature}")
                self._list_available_features()
        elif action == "disable" and feature:
            if self.config_manager.disable_feature(feature):
                print(f"❌ Disabled feature: {feature}")
            else:
                print(f"❌ Unknown feature: {feature}")
        elif action == "reset":
            self.config_manager.reset_to_defaults()
            print("🔄 Configuration reset to defaults")
        elif action == "experimental":
            self.config_manager.enable_experimental_mode()
            print("🧪 Enabled all experimental features")
        elif action == "list":
            self._list_available_features()
        else:
            print(
                "❌ Invalid config action. Use: show, enable, disable, reset, experimental, list")

    def _show_config(self):
        """Display current configuration"""
        features = self.config_manager.list_features()
        experimental = self.config_manager.list_experimental_features()

        print("⚙️  Current Configuration:\n")

        print("🎛️  Features:")
        for name, enabled in features.items():
            icon = "✅" if enabled else "❌"
            exp_marker = " (experimental)" if name in experimental else ""
            print(f"   {icon} {name}{exp_marker}")

        print(f"\n🤖 LLM Configuration:")
        llm_config = self.config_manager.get_llm_config()
        print(f"   Provider: {llm_config.default_provider}")
        print(f"   Ollama URL: {llm_config.ollama_url}")
        print(f"   Models configured: {len(llm_config.models)}")

        print(f"\n💾 Database Configuration:")
        db_config = self.config_manager.get_database_config()
        print(f"   Path: {db_config.path}")
        print(f"   Cleanup after: {db_config.cleanup_days} days")

    def _list_available_features(self):
        """List all available features"""
        features = self.config_manager.list_features()
        experimental = self.config_manager.list_experimental_features()

        print("\n🎛️  Available Features:")
        print("\nStable Features:")
        for name, enabled in features.items():
            if name not in experimental:
                status = "enabled" if enabled else "disabled"
                print(f"   {name}: {status}")

        print("\nExperimental Features:")
        for name, enabled in experimental.items():
            status = "enabled" if enabled else "disabled"
            print(f"   {name}: {status}")

        print(f"\n💡 Usage:")
        print(f"   digestr config enable <feature_name>")
        print(f"   digestr config disable <feature_name>")
        print(f"   digestr config experimental  # Enable all experimental")

    async def interactive_session(self, hours: int = 24, category: Optional[str] = None):
        """Start an interactive session with recent articles"""
        if not self.config_manager.is_feature_enabled('interactive_mode'):
            print("⚠️  Interactive mode is not enabled.")
            print("💡 Enable with: digestr config enable interactive_mode")
            return

        # Get recent articles for context
        articles = self.db_manager.get_recent_articles(
            hours=hours,
            category=category,
            limit=30,
            unprocessed_only=False  # Include processed articles for context
        )

        if not articles:
            print(f"❌ No articles found from the last {hours} hours.")
            print("💡 Try: digestr briefing  # to fetch latest news first")
            return

        # Convert to legacy format
        legacy_articles = [
            {
                'title': article.title,
                'summary': article.summary,
                'content': article.content,
                'url': article.url,
                'category': article.category,
                'source': article.source,
                'published_date': article.published_date,
                'importance_score': article.importance_score
            }
            for article in articles
        ]

        print(f"🎯 Starting interactive session with {len(articles)} articles")
        print("💡 Ask questions about the news or type 'exit' to quit\n")

        session = InteractiveSession(legacy_articles, self.llm_provider)
        await session.start()

    def cleanup_database(self, days: int = 30, dry_run: bool = False):
        """Clean up old articles from database"""
        if dry_run:
            # TODO: Implement dry run mode
            print(f"🔍 Dry run: Would remove articles older than {days} days")
            return

        removed_count = self.db_manager.cleanup_old_articles(days)
        if removed_count > 0:
            print(f"🧹 Removed {removed_count} articles older than {days} days")
        else:
            print(f"✨ No articles older than {days} days found")


def create_parser():
    """Create the argument parser for the CLI"""
    parser = argparse.ArgumentParser(
        description="Digestr.ai - Intelligent news summarization and analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  digestr briefing                           # Standard comprehensive briefing
  digestr briefing --interactive             # Briefing with follow-up questions
  digestr briefing --category tech --hours 12  # Tech news from last 12 hours
  digestr briefing --style quick             # Quick summary style
  digestr interactive                        # Start interactive session
  digestr config show                        # Show current configuration
  digestr config enable interactive_mode     # Enable interactive features
  digestr status                             # System status overview
        """
    )

    subparsers = parser.add_subparsers(
        dest='command', help='Available commands')

    # Briefing command
    briefing_parser = subparsers.add_parser(
        'briefing', help='Generate news briefing')
    briefing_parser.add_argument('--category', '-c', choices=['tech', 'world_news', 'sports', 'cutting_edge', 'business', 'security'],
                                 help='Focus on specific category')
    briefing_parser.add_argument('--hours', '-h', type=int, default=24,
                                 help='Hours of news to analyze (default: 24)')
    briefing_parser.add_argument('--style', '-s', choices=['comprehensive', 'quick', 'analytical', 'casual'],
                                 default='comprehensive', help='Briefing style (default: comprehensive)')
    briefing_parser.add_argument('--interactive', '-i', action='store_true',
                                 help='Start interactive mode after briefing')
    briefing_parser.add_argument('--model', '-m', help='Specific model to use')
    briefing_parser.add_argument('--fetch-only', '-f', action='store_true',
                                 help='Only fetch articles, skip summarization')

    # Interactive command
    interactive_parser = subparsers.add_parser(
        'interactive', help='Start interactive session')
    interactive_parser.add_argument('--hours', '-h', type=int, default=24,
                                    help='Hours of articles to include (default: 24)')
    interactive_parser.add_argument('--category', '-c', choices=['tech', 'world_news', 'sports', 'cutting_edge', 'business', 'security'],
                                    help='Focus on specific category')

    # Config command
    config_parser = subparsers.add_parser(
        'config', help='Manage configuration')
    config_parser.add_argument('action', choices=['show', 'enable', 'disable', 'reset', 'experimental', 'list'],
                               help='Configuration action')
    config_parser.add_argument(
        'feature', nargs='?', help='Feature name for enable/disable')
    config_parser.add_argument(
        'value', nargs='?', help='Value for setting (future use)')

    # Status command
    subparsers.add_parser('status', help='Show system status')

    # Cleanup command
    cleanup_parser = subparsers.add_parser(
        'cleanup', help='Database maintenance')
    cleanup_parser.add_argument('--days', '-d', type=int, default=30,
                                help='Remove articles older than N days (default: 30)')
    cleanup_parser.add_argument('--dry-run', action='store_true',
                                help='Show what would be removed without actually removing')

    return parser


async def main():
    """Main CLI entry point"""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Set up logging level based on verbosity
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        cli = DigestrCLI()

        if args.command == 'briefing':
            await cli.run_briefing(
                category=args.category,
                hours=args.hours,
                style=args.style,
                interactive=args.interactive,
                model=args.model,
                fetch_only=args.fetch_only
            )

        elif args.command == 'interactive':
            await cli.interactive_session(
                hours=args.hours,
                category=args.category
            )

        elif args.command == 'config':
            cli.manage_config(args.action, args.feature, args.value)

        elif args.command == 'status':
            await cli.show_status()

        elif args.command == 'cleanup':
            cli.cleanup_database(args.days, args.dry_run)

    except KeyboardInterrupt:
        print("\n👋 Operation cancelled")
        sys.exit(0)
    except Exception as e:
        logger.error(f"CLI error: {e}")
        print(f"❌ Error: {e}")
        print("💡 Try: digestr status  # to check system health")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
