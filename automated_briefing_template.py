import asyncio
import sys
from pathlib import Path

sys.path.insert(0, 'src')

async def automated_briefing_direct():
    try:
        from digestr.core.database import DatabaseManager
        from digestr.llm_providers.ollama import OllamaProvider
        import smtplib, ssl
        from email.message import EmailMessage
        from datetime import datetime
        
        # Direct email configuration (known working values)
        smtp_server = 'smtp.gmail.com'
        smtp_port = 465
        sender_email = 'YOUR_EMAIL@gmail.com'
        sender_password = 'YOUR_APP_PASSWORD'
        
        # Determine briefing style based on time
        hour = datetime.now().hour
        if hour < 10:
            style = 'comprehensive'
            style_name = 'Morning'
        elif hour < 16:
            style = 'quick'
            style_name = 'Midday'
        else:
            style = 'analytical'
            style_name = 'Evening'
        
        print(f'Starting {style_name} briefing...')
        
        # Get articles
        db = DatabaseManager()
        articles = db.get_recent_articles(hours=24, limit=12, unprocessed_only=True)
        
        if not articles:
            print('No new articles - skipping briefing')
            return
        
        print(f'Found {len(articles)} articles to process')
        
        # Convert to dict format
        article_dicts = []
        for a in articles:
            article_dicts.append({
                'title': a.title,
                'summary': a.summary,
                'content': a.content,
                'category': a.category,
                'source': a.source,
                'importance_score': a.importance_score
            })
        
        # Generate AI briefing
        print('Generating AI briefing...')
        llm = OllamaProvider()
        briefing = await llm.generate_briefing(article_dicts, briefing_type=style)
        
        if briefing.startswith('Error:'):
            print(f'AI generation failed: {briefing}')
            return
        
        print('AI briefing generated successfully')
        print(f'Briefing length: {len(briefing)} characters')
        
        # Send email - Simple working version
        print(f'Sending email via {smtp_server}:{smtp_port}...')
        
        msg = EmailMessage()
        msg['Subject'] = f'📰 {style_name} Briefing - {datetime.now().strftime("%B %d, %Y")}'
        msg['From'] = sender_email
        import yaml
        config_path = Path('C:/Users/robin/AppData/Roaming/digestr/plugins/conversation-export/config.yaml')
        with open(config_path, 'r') as f:
            plugin_config = yaml.safe_load(f)
        
        # Get recipients for current time period
        if hour < 10:
            recipients = plugin_config['scheduling']['briefings']['morning']['recipients']
        elif hour < 16:
            recipients = plugin_config['scheduling']['briefings']['midday']['recipients']
        else:
            recipients = plugin_config['scheduling']['briefings']['evening']['recipients']
        
        # Send to all recipients
        msg['To'] = ', '.join(recipients)
        print(f'Sending to: {recipients}')
        msg.set_content(briefing)
        
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(smtp_server, smtp_port, context=context) as server:
            server.login(sender_email, sender_password)
            server.send_message(msg)
        
        print('Email sent successfully!')
        
        # Mark as processed
        article_urls = [a.url for a in articles]
        db.mark_articles_processed(article_urls)
        
        print(f'{style_name} briefing completed successfully!')
        
    except Exception as e:
        print(f'Briefing failed: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(automated_briefing_direct())
