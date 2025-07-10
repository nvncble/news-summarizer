"""
Digestr Analysis Module
Advanced analysis capabilities including trend correlation and cross-source analysis
"""

from .trend_structures import (
    TrendingTopic, 
    TrendCorrelation, 
    GeographicConfig, 
    CrossSourceTrendAnalysis
)
from .trend_correlation_engine import TrendCorrelationEngine
from .trend_aware_briefing_generator import TrendAwareBriefingGenerator



__all__ = [
    'TrendingTopic',
    'TrendCorrelation', 
    'GeographicConfig',
    'CrossSourceTrendAnalysis',
    'TrendCorrelationEngine',
    'TrendAwareBriefingGenerator',
    'ContentSource',
     'QualityFilter',
      'SourceManager', 
      'Trends24Source'
]