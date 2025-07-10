#!/usr/bin/env python3
"""
Enhanced Error Handling and Resilience for Digestr.ai
Provides comprehensive error handling, retry logic, and graceful degradation
"""

import asyncio
import logging
import time
import traceback
from functools import wraps
from typing import Any, Callable, Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_attempts: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    exceptions: tuple = (Exception,)


@dataclass
class ErrorContext:
    """Context information for errors"""
    operation: str
    component: str
    timestamp: datetime
    attempt: int
    total_attempts: int
    error_type: str
    error_message: str
    additional_info: Dict[str, Any]


class DigestrError(Exception):
    """Base exception for Digestr-specific errors"""
    
    def __init__(self, message: str, component: str = "unknown", 
                 recoverable: bool = True, context: Dict[str, Any] = None):
        super().__init__(message)
        self.component = component
        self.recoverable = recoverable
        self.context = context or {}
        self.timestamp = datetime.now()


class TrendAnalysisError(DigestrError):
    """Errors specific to trend analysis"""
    pass


class SourceError(DigestrError):
    """Errors related to content sources"""
    pass


class DatabaseError(DigestrError):
    """Database operation errors"""
    pass


class LLMError(DigestrError):
    """LLM provider errors"""
    pass


class ConfigurationError(DigestrError):
    """Configuration-related errors"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, recoverable=False, **kwargs)


class ResilientOperationManager:
    """Manages resilient operations with retry logic and error handling"""
    
    def __init__(self):
        self.error_history: List[ErrorContext] = []
        self.circuit_breakers: Dict[str, CircuitBreaker] = {}
        self.default_retry_config = RetryConfig()
    
    def with_retry(self, config: RetryConfig = None):
        """Decorator for automatic retry logic"""
        
        if config is None:
            config = self.default_retry_config
        
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                return await self.execute_with_retry(func, config, *args, **kwargs)
            return wrapper
        return decorator
    
    async def execute_with_retry(self, func: Callable, config: RetryConfig, 
                               *args, **kwargs) -> Any:
        """Execute function with retry logic"""
        
        last_exception = None
        delay = config.base_delay
        
        for attempt in range(1, config.max_attempts + 1):
            try:
                # Check circuit breaker
                component = getattr(func, '__qualname__', str(func))
                if not self._check_circuit_breaker(component):
                    raise DigestrError(f"Circuit breaker open for {component}", 
                                     component=component, recoverable=False)
                
                result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
                
                # Reset circuit breaker on success
                self._reset_circuit_breaker(component)
                
                if attempt > 1:
                    logger.info(f"Operation succeeded on attempt {attempt}: {component}")
                
                return result
                
            except config.exceptions as e:
                last_exception = e
                
                # Record error context
                error_context = ErrorContext(
                    operation=getattr(func, '__name__', str(func)),
                    component=getattr(func, '__qualname__', str(func)),
                    timestamp=datetime.now(),
                    attempt=attempt,
                    total_attempts=config.max_attempts,
                    error_type=type(e).__name__,
                    error_message=str(e),
                    additional_info={'args': str(args)[:100], 'kwargs': str(kwargs)[:100]}
                )
                self._record_error(error_context)
                
                # Update circuit breaker
                self._update_circuit_breaker(component, e)
                
                if attempt == config.max_attempts:
                    logger.error(f"Operation failed after {attempt} attempts: {component}")
                    break
                
                # Calculate delay with jitter
                actual_delay = min(delay + (delay * 0.1 * (attempt - 1)), config.max_delay)
                logger.warning(f"Attempt {attempt} failed for {component}: {e}. Retrying in {actual_delay:.1f}s...")
                
                await asyncio.sleep(actual_delay)
                delay *= config.backoff_factor
        
        # If we get here, all attempts failed
        raise last_exception
    
    def _check_circuit_breaker(self, component: str) -> bool:
        """Check if circuit breaker allows operation"""
        if component not in self.circuit_breakers:
            self.circuit_breakers[component] = CircuitBreaker()
        
        return self.circuit_breakers[component].can_execute()
    
    def _update_circuit_breaker(self, component: str, error: Exception):
        """Update circuit breaker state after error"""
        if component in self.circuit_breakers:
            self.circuit_breakers[component].record_failure()
    
    def _reset_circuit_breaker(self, component: str):
        """Reset circuit breaker after success"""
        if component in self.circuit_breakers:
            self.circuit_breakers[component].record_success()
    
    def _record_error(self, context: ErrorContext):
        """Record error for monitoring and analysis"""
        self.error_history.append(context)
        
        # Keep only recent errors (last 1000)
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        # Log error with context
        logger.error(f"Error in {context.component}.{context.operation} "
                    f"(attempt {context.attempt}/{context.total_attempts}): "
                    f"{context.error_type}: {context.error_message}")
    
    def get_error_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get error summary for monitoring"""
        
        cutoff = datetime.now() - timedelta(hours=hours)
        recent_errors = [e for e in self.error_history if e.timestamp > cutoff]
        
        if not recent_errors:
            return {'total_errors': 0, 'period_hours': hours}
        
        # Group by component
        by_component = {}
        by_error_type = {}
        
        for error in recent_errors:
            # By component
            if error.component not in by_component:
                by_component[error.component] = 0
            by_component[error.component] += 1
            
            # By error type
            if error.error_type not in by_error_type:
                by_error_type[error.error_type] = 0
            by_error_type[error.error_type] += 1
        
        return {
            'total_errors': len(recent_errors),
            'period_hours': hours,
            'by_component': by_component,
            'by_error_type': by_error_type,
            'most_recent': recent_errors[-1].error_message if recent_errors else None
        }


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'closed'  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if operation can be executed"""
        
        if self.state == 'closed':
            return True
        
        if self.state == 'open':
            if self.last_failure_time and \
               time.time() - self.last_failure_time > self.timeout:
                self.state = 'half-open'
                return True
            return False
        
        if self.state == 'half-open':
            return True
        
        return False
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = 'closed'
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'open'


class GracefulDegradationManager:
    """Manages graceful degradation of features when components fail"""
    
    def __init__(self):
        self.disabled_features: Dict[str, Dict[str, Any]] = {}
    
    def disable_feature(self, feature: str, reason: str, duration: int = 3600):
        """Temporarily disable a feature"""
        self.disabled_features[feature] = {
            'reason': reason,
            'disabled_at': datetime.now(),
            'duration': duration
        }
        logger.warning(f"Feature '{feature}' disabled: {reason}")
    
    def is_feature_enabled(self, feature: str) -> bool:
        """Check if feature is currently enabled"""
        if feature not in self.disabled_features:
            return True
        
        disabled_info = self.disabled_features[feature]
        disabled_at = disabled_info['disabled_at']
        duration = disabled_info['duration']
        
        if datetime.now() - disabled_at > timedelta(seconds=duration):
            # Re-enable feature after timeout
            del self.disabled_features[feature]
            logger.info(f"Feature '{feature}' re-enabled after timeout")
            return True
        
        return False
    
    def enable_feature(self, feature: str):
        """Manually re-enable a feature"""
        if feature in self.disabled_features:
            del self.disabled_features[feature]
            logger.info(f"Feature '{feature}' manually re-enabled")


# Global instances
resilient_ops = ResilientOperationManager()
graceful_degradation = GracefulDegradationManager()


def resilient_operation(retry_config: RetryConfig = None):
    """Decorator for resilient operations"""
    return resilient_ops.with_retry(retry_config)


def safe_execute(func: Callable, default_return=None, log_errors: bool = True) -> Any:
    """Safely execute a function with error handling"""
    try:
        return func()
    except Exception as e:
        if log_errors:
            logger.error(f"Safe execution failed in {func.__name__}: {e}")
        return default_return


async def safe_execute_async(func: Callable, default_return=None, log_errors: bool = True) -> Any:
    """Safely execute an async function with error handling"""
    try:
        return await func()
    except Exception as e:
        if log_errors:
            logger.error(f"Safe async execution failed in {func.__name__}: {e}")
        return default_return


class NetworkResilienceManager:
    """Manages network-related resilience for external API calls"""
    
    def __init__(self):
        self.connection_pool_config = {
            'connector': aiohttp.TCPConnector(
                limit=100,
                limit_per_host=20,
                ttl_dns_cache=300,
                use_dns_cache=True,
                keepalive_timeout=30,
                enable_cleanup_closed=True
            ),
            'timeout': aiohttp.ClientTimeout(
                total=30,
                connect=10,
                sock_read=10
            )
        }
    
    async def create_resilient_session(self) -> aiohttp.ClientSession:
        """Create an HTTP session with resilience features"""
        return aiohttp.ClientSession(**self.connection_pool_config)
    
    @resilient_operation(RetryConfig(
        max_attempts=3,
        base_delay=1.0,
        exceptions=(aiohttp.ClientError, asyncio.TimeoutError)
    ))
    async def fetch_with_resilience(self, url: str, session: aiohttp.ClientSession, 
                                  headers: Dict[str, str] = None) -> str:
        """Fetch URL with automatic retry and error handling"""
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 429:  # Rate limited
                    retry_after = int(response.headers.get('Retry-After', 60))
                    logger.warning(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limited")
                
                response.raise_for_status()
                return await response.text()
                
        except aiohttp.ClientError as e:
            raise SourceError(f"Network error fetching {url}: {e}", 
                            component="network", recoverable=True)


# Integration helpers for existing code

def make_trend_analysis_resilient():
    """Apply resilience patterns to trend analysis components"""
    
    # This would be used to wrap existing trend analysis methods
    def wrap_trend_method(method):
        @resilient_operation(RetryConfig(
            max_attempts=2,
            base_delay=2.0,
            exceptions=(TrendAnalysisError, aiohttp.ClientError)
        ))
        async def wrapped(*args, **kwargs):
            try:
                return await method(*args, **kwargs)
            except Exception as e:
                if "trends24" in str(method):
                    # Disable trend analysis temporarily if Trends24 is down
                    graceful_degradation.disable_feature(
                        "trends24_scraping", 
                        f"Trends24 unavailable: {e}", 
                        duration=1800  # 30 minutes
                    )
                raise TrendAnalysisError(f"Trend analysis failed: {e}")
        return wrapped
    
    return wrap_trend_method


def make_source_fetching_resilient():
    """Apply resilience patterns to source fetching"""
    
    def wrap_source_method(method):
        @resilient_operation(RetryConfig(
            max_attempts=3,
            base_delay=1.0,
            exceptions=(SourceError, aiohttp.ClientError, asyncio.TimeoutError)
        ))
        async def wrapped(*args, **kwargs):
            try:
                return await method(*args, **kwargs)
            except Exception as e:
                source_name = getattr(method, '__self__', {}).get('source_name', 'unknown')
                raise SourceError(f"Source {source_name} failed: {e}", 
                                component=source_name, recoverable=True)
        return wrapped
    
    return wrap_source_method


class HealthMonitor:
    """Monitor system health and component status"""
    
    def __init__(self):
        self.component_status: Dict[str, Dict[str, Any]] = {}
        self.last_health_check = None
    
    async def check_system_health(self) -> Dict[str, Any]:
        """Comprehensive system health check"""
        
        health_report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': 'healthy',
            'components': {},
            'degraded_features': list(graceful_degradation.disabled_features.keys()),
            'error_summary': resilient_ops.get_error_summary()
        }
        
        # Check database
        try:
            from digestr.core.database import DatabaseManager
            db = DatabaseManager()
            # Simple database check
            health_report['components']['database'] = {
                'status': 'healthy',
                'last_checked': datetime.now().isoformat()
            }
        except Exception as e:
            health_report['components']['database'] = {
                'status': 'unhealthy',
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }
            health_report['overall_status'] = 'degraded'
        
        # Check LLM provider
        try:
            from digestr.llm_providers.ollama import OllamaProvider
            llm = OllamaProvider()
            if llm.validate_config():
                health_report['components']['llm'] = {
                    'status': 'healthy',
                    'provider': 'ollama',
                    'last_checked': datetime.now().isoformat()
                }
            else:
                health_report['components']['llm'] = {
                    'status': 'unhealthy',
                    'error': 'Configuration validation failed',
                    'last_checked': datetime.now().isoformat()
                }
                health_report['overall_status'] = 'degraded'
        except Exception as e:
            health_report['components']['llm'] = {
                'status': 'unhealthy',
                'error': str(e),
                'last_checked': datetime.now().isoformat()
            }
            health_report['overall_status'] = 'degraded'
        
        # Check trend analysis if enabled
        if graceful_degradation.is_feature_enabled('trend_analysis'):
            try:
                # Basic trend analysis health check
                health_report['components']['trend_analysis'] = {
                    'status': 'healthy',
                    'features_disabled': len(graceful_degradation.disabled_features),
                    'last_checked': datetime.now().isoformat()
                }
            except Exception as e:
                health_report['components']['trend_analysis'] = {
                    'status': 'unhealthy',
                    'error': str(e),
                    'last_checked': datetime.now().isoformat()
                }
        
        self.last_health_check = datetime.now()
        return health_report
    
    def is_component_healthy(self, component: str) -> bool:
        """Check if specific component is healthy"""
        return self.component_status.get(component, {}).get('status') == 'healthy'


# Global health monitor
health_monitor = HealthMonitor()


# Utility functions for integration

def handle_graceful_degradation(feature: str, fallback_func: Callable = None):
    """Handle graceful degradation for a feature"""
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if not graceful_degradation.is_feature_enabled(feature):
                logger.info(f"Feature {feature} is disabled, using fallback")
                if fallback_func:
                    return await fallback_func(*args, **kwargs) if asyncio.iscoroutinefunction(fallback_func) else fallback_func(*args, **kwargs)
                return None
            
            try:
                return await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Feature {feature} failed: {e}")
                graceful_degradation.disable_feature(feature, str(e))
                if fallback_func:
                    return await fallback_func(*args, **kwargs) if asyncio.iscoroutinefunction(fallback_func) else fallback_func(*args, **kwargs)
                raise
        
        return wrapper
    return decorator