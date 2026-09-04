#!/usr/bin/env python3
# =============================================================================
# CIRCUIT BREAKER IMPLEMENTATION FOR ALBERT
# Proporciona resiliencia a fallos en dependencias externas
# =============================================================================

import time
import threading
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Failing, requests fail fast
    HALF_OPEN = "half_open" # Testing if service recovered

@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 5          # Number of failures before opening
    recovery_timeout: int = 30          # Seconds to wait before trying half-open
    expected_exception: type = Exception # Exception type that counts as failure
    success_threshold: int = 3          # Successes needed in half-open to close
    timeout: float = 30.0               # Timeout for the protected call

@dataclass
class CircuitBreakerStats:
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[float] = None
    last_state_change: float = field(default_factory=time.time)
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    timeouts: int = 0

class CircuitBreakerOpenException(Exception):
    """Excepción lanzada cuando el circuit breaker está abierto"""
    pass

class CircuitBreaker:
    """
    Implementación del patrón Circuit Breaker para proteger llamadas a servicios externos.
    """
    
    def __init__(self, name: str, config: CircuitBreakerConfig = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.stats = CircuitBreakerStats()
        self._lock = threading.RLock()
        
        # Para estado half-open: contar éxitos consecutivos
        self._consecutive_successes = 0
        
    def call(self, func: Callable[..., Any], *args, **kwargs) -> Any:
        """
        Ejecuta la función protegida por el circuit breaker.
        """
        with self._lock:
            self.stats.total_calls += 1
            
            # Verificar estado actual
            if self.state == CircuitState.OPEN:
                if self._should_attempt_reset():
                    self._set_state(CircuitState.HALF_OPEN)
                else:
                    raise CircuitBreakerOpenException(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Last failure: {self.stats.last_failure_time}"
                    )
            
            # Intentar la llamada
            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Verificar timeout
                if elapsed > self.config.timeout:
                    raise TimeoutError(f"Call timed out after {elapsed:.2f}s")
                
                self._on_success()
                return result
                
            except self.config.expected_exception as e:
                self._on_failure()
                raise e
            except TimeoutError as e:
                self._on_timeout()
                raise e
            except Exception as e:
                # Tratar cualquier otra excepción como fallo
                self._on_failure()
                raise e
    
    def _should_attempt_reset(self) -> bool:
        """Determina si es momento de intentar pasar a half-open"""
        return (
            self.stats.last_failure_time is not None and
            time.time() - self.stats.last_failure_time >= self.config.recovery_timeout
        )
    
    def _on_success(self) -> None:
        """Maneja una llamada exitosa"""
        self.stats.success_count += 1
        self.stats.successful_calls += 1
        self.stats.last_state_change = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            self._consecutive_successes += 1
            if self._consecutive_successes >= self.config.success_threshold:
                self._set_state(CircuitState.CLOSED)
                self._reset_counters()
        elif self.state == CircuitState.CLOSED:
            # Reset failure count on success in closed state
            self.stats.failure_count = 0
    
    def _on_failure(self) -> None:
        """Maneja una llamada fallida"""
        self.stats.failure_count += 1
        self.stats.failed_calls += 1
        self.stats.last_failure_time = time.time()
        self.stats.last_state_change = time.time()
        
        if self.state == CircuitState.CLOSED:
            if self.stats.failure_count >= self.config.failure_threshold:
                self._set_state(CircuitState.OPEN)
        elif self.state == CircuitState.HALF_OPEN:
            # Cualquier failure en half-open vuelve a open
            self._set_state(CircuitState.OPEN)
            self._consecutive_successes = 0
    
    def _on_timeout(self) -> None:
        """Maneja un timeout"""
        self._on_failure()  # Tratar timeout como fallo
        self.stats.timeouts += 1
    
    def _set_state(self, state: CircuitState) -> None:
        """Cambia el estado del circuit breaker"""
        old_state = self.state
        self.state = state
        self.stats.last_state_change = time.time()
        logger.info(
            f"Circuit breaker '{self.name}' changed state: "
            f"{old_state.value} -> {state.value}"
        )
    
    def _reset_counters(self) -> None:
        """Reinicia contadores después de recuperación exitosa"""
        self.stats.failure_count = 0
        self.stats.success_count = 0
        self._consecutive_successes = 0
    
    def get_state(self) -> dict:
        """Devuelve el estado actual del circuit breaker para monitoreo"""
        with self._lock:
            return {
                "name": self.name,
                "state": self.state.value,
                "failure_count": self.stats.failure_count,
                "success_count": self.stats.success_count,
                "total_calls": self.stats.total_calls,
                "successful_calls": self.stats.successful_calls,
                "failed_calls": self.stats.failed_calls,
                "timeouts": self.stats.timeouts,
                "last_failure_time": self.stats.last_failure_time,
                "last_state_change": self.stats.last_state_change
            }
    
    def reset(self) -> None:
        """Fuerza el reset del circuit breaker a estado cerrado"""
        with self._lock:
            self._set_state(CircuitState.CLOSED)
            self._reset_counters()
            logger.info(f"Circuit breaker '{self.name}' manually reset")

# Registry global para acceder a los circuit breakers desde cualquier lugar
_circuit_breakers = {}

def get_circuit_breaker(name: str, config: CircuitBreakerConfig = None) -> CircuitBreaker:
    """Obtiene o crea un circuit breaker con el nombre dado"""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config)
    return _circuit_breakers[name]

def get_all_circuit_breaker_states() -> dict:
    """Obtiene el estado de todos los circuit breakers registrados"""
    return {name: cb.get_state() for name, cb in _circuit_breakers.items()}