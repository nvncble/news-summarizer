"""
Abstract base classes for content sources
"""

from abc import ABC, abstractmethod
from typing import List, Dict
from digestr.core.database import Article


class ContentSource(ABC):
    """Abstract base class for all content sources"""
    
    @abstractmethod
    async def fetch_content(self, hours: int = 24) -> List[Article]:
        """Fetch content from the source and return as Article objects"""
        pass
    
    @abstractmethod
    def get_source_type(self) -> str:
        """Return the source type identifier"""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate source configuration"""
        pass


class QualityFilter(ABC):
    """Abstract base class for content quality filtering"""
    
    @abstractmethod
    def is_quality_content(self, content: Dict) -> bool:
        """Determine if content meets quality standards"""
        pass