"""System monitoring and health check utilities."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.shared.error_handling import (
    get_all_circuit_breakers,
    get_degradation_manager,
    CircuitState
)

logger = logging.getLogger(__name__)


class SystemHealthMonitor:
    """
    Monitor system health including circuit breakers and service availability.
    
    Provides comprehensive health status for all system components.
    """
    
    def __init__(self):
        """Initialize system health monitor."""
        self.degradation_manager = get_degradation_manager()
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get comprehensive system health status.
        
        Returns:
            Dictionary with health status for all components
        """
        circuit_breakers = get_all_circuit_breakers()
        service_status = self.degradation_manager.get_status()
        
        # Determine overall health
        all_healthy = True
        warnings = []
        errors = []
        
        # Check circuit breakers
        for name, breaker in circuit_breakers.items():
            if breaker.state == CircuitState.OPEN:
                all_healthy = False
                errors.append(f"Circuit breaker '{name}' is OPEN")
            elif breaker.state == CircuitState.HALF_OPEN:
                warnings.append(f"Circuit breaker '{name}' is HALF_OPEN (testing recovery)")
        
        # Check service availability
        for service_name, status in service_status.items():
            if not status['available']:
                all_healthy = False
                errors.append(f"Service '{service_name}' is unavailable")
            
            # Check for stale fallback data
            if status['has_fallback'] and status['data_age_seconds']:
                if status['data_age_seconds'] > 300:  # 5 minutes
                    warnings.append(
                        f"Service '{service_name}' fallback data is stale "
                        f"({status['data_age_seconds']:.0f}s old)"
                    )
        
        return {
            'timestamp': datetime.utcnow().isoformat(),
            'overall_healthy': all_healthy,
            'circuit_breakers': {
                name: breaker.get_status()
                for name, breaker in circuit_breakers.items()
            },
            'services': service_status,
            'warnings': warnings,
            'errors': errors
        }
    
    def get_circuit_breaker_summary(self) -> Dict[str, str]:
        """
        Get summary of all circuit breaker states.
        
        Returns:
            Dictionary mapping circuit breaker names to states
        """
        circuit_breakers = get_all_circuit_breakers()
        return {
            name: breaker.state.value
            for name, breaker in circuit_breakers.items()
        }
    
    def get_service_availability(self) -> Dict[str, bool]:
        """
        Get availability status for all services.
        
        Returns:
            Dictionary mapping service names to availability
        """
        service_status = self.degradation_manager.get_status()
        return {
            name: status['available']
            for name, status in service_status.items()
        }
    
    def is_system_healthy(self) -> bool:
        """
        Check if system is overall healthy.
        
        Returns:
            True if all components are healthy, False otherwise
        """
        status = self.get_health_status()
        return status['overall_healthy']
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """
        Get list of active alerts.
        
        Returns:
            List of alert dictionaries
        """
        status = self.get_health_status()
        alerts = []
        
        # Add error alerts
        for error in status['errors']:
            alerts.append({
                'severity': 'error',
                'message': error,
                'timestamp': status['timestamp']
            })
        
        # Add warning alerts
        for warning in status['warnings']:
            alerts.append({
                'severity': 'warning',
                'message': warning,
                'timestamp': status['timestamp']
            })
        
        return alerts
    
    def log_health_status(self):
        """Log current health status."""
        status = self.get_health_status()
        
        if status['overall_healthy']:
            logger.info("System health check: All systems operational")
        else:
            logger.warning(
                f"System health check: Issues detected. "
                f"Errors: {len(status['errors'])}, Warnings: {len(status['warnings'])}"
            )
            
            for error in status['errors']:
                logger.error(f"Health check error: {error}")
            
            for warning in status['warnings']:
                logger.warning(f"Health check warning: {warning}")


# Global health monitor instance
_health_monitor: SystemHealthMonitor = None


def get_health_monitor() -> SystemHealthMonitor:
    """Get or create global health monitor instance."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = SystemHealthMonitor()
    return _health_monitor
