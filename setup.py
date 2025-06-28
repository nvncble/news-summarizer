from setuptools import setup, find_packages

setup(
    name="news-summarizer",
    version="1.0.0",
    description="Advanced RSS feed summarizer with AI integration",
    author="Tian Robinson",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "aiohttp>=3.8.0",
        "feedparser>=6.0.0",
        "requests>=2.28.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "news-summarizer=rss_summarizer:main",
        ],
    },
)