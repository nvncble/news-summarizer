@echo off
cd /d "C:\Users\robin\news-summarizer"
chcp 65001 > nul

echo Starting Digestr automated briefing...
python automated_briefing_direct.py >> "C:\Users\robin\.digestr\logs\briefing.log" 2>&1
echo Briefing process completed.
