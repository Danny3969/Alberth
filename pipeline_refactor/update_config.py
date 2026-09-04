import pathlib, yaml, re, sys

BASE = pathlib.Path('/Users/digitalspace/.openclaw/workspace/pipeline_refactor')
CONFIG_PATH = BASE / 'config.yaml'
SRC = BASE / 'alberth_master_py.py'
DST = BASE / 'alberth_master_py.py.new'

with open(CONFIG_PATH, 'rt') as f:
    cfg = yaml.safe_load(f)

def get(*keys):
    d = cfg
    for k in keys:
        d = d.get(k, {})
    return d

# Build config object
class SimpleConf:
    def __init__(self, cfg):
        self.service_timeouts = SimpleNamespace(**cfg['service_timeouts'])
        self.circuit_breaker = SimpleNamespace(
            stt_cloud=SimpleNamespace(**cfg['circuit_breaker']['stt_cloud']),
            stt_local=SimpleNamespace(**cfg['circuit_breaker']['stt_local']),
            agent=SimpleNamespace(**cfg['circuit_breaker']['agent']),
            tts=SimpleNamespace(**cfg['circuit_breaker']['tts']),
            helper=SimpleNamespace(**cfg['circuit_breaker']['helper'])
        )
        self.cache = SimpleNamespace(**cfg['cache'])
        self.metrics = SimpleNamespace(**cfg['metrics'])
        self.wakeword = SimpleNamespace(**cfg['wakeword'])

from types import SimpleNamespace
CONF = SimpleConf(cfg)

src = SRC.read_text(encoding='utf-8')

import_block = '''import os
import sys
import json
import time
import subprocess
import threading
import signal
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, Callable
import logging
import http.server
import socketserver
import yaml
from pydantic import BaseModel, Field, validator
'''

import_end = src.find('# ======================= CACHE =======================')
if import_end == -1:
    import_end = src.find('\n#')
new_src = src[:import_end] + import_block + src[import_end:]

model_defs = '''
# ======================= CONFIGURATION MODELS =======================
class PathsConfig(BaseModel):
    workspace_dir: str
    voice_dir: str
    input_dir: str
    output_dir: str
    log_dir: str
    lock_file: str

class TimeoutConfig(BaseModel):
    stt_cloud: int
    stt_local: int
    talamo: int
    helper: int
    agent: int
    tts: int

class CBConfig(BaseModel):
    failure_threshold: int
    recovery_timeout: int
    timeout: float

class CircuitBreakerConfigModel(BaseModel):
    stt_cloud: CBConfig
    stt_local: CBConfig
    agent: CBConfig
    tts: CBConfig
    helper: CBConfig

class CacheConfig(BaseModel):
    ttl_seconds: int
    maxsize: int

class MetricsConfig(BaseModel):
    port: int

class WakeWordConfig(BaseModel):
    enabled: bool
    session_timeout: int

class AppConfig(BaseModel):
    paths: PathsConfig
    service_timeouts: TimeoutConfig
    circuit_breaker: CircuitBreakerConfigModel
    cache: CacheConfig
    metrics: MetricsConfig
    wakeword: WakeWordConfig

    @validator('*', pre=True)
    def expand_env_vars(cls, v):
        if isinstance(v, str):
            return os.path.expandvars(v)
        elif isinstance(v, dict):
            return {k: os.path.expandvars(str(v2)) for k, v2 in v.items()}
        elif isinstance(v, list):
            return [os.path.expandvars(str(i)) for i in v]
        return v

# Load configuration
CONFIG_PATH = Path(__file__).with_name('config.yaml')
if not CONFIG_PATH.is_file():
    raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
with open(CONFIG_PATH, 'rt', encoding='utf-8') as f:
    raw_cfg = yaml.safe_load(f)
CONF = AppConfig(**raw_cfg)

# ======================= LOGGER & CONFIG =======================
'''

logger_line = new_src.find('logger = logging.getLogger(__name__)')
new_src = new_src[:logger_line] + model_defs + '\n' + new_src[logger_line:]

# Replace paths section
start = new_src.find('# Rutas base')
end = new_src.find('# Asegurar que los directorios existen')
replacement = '''# Rutas base
WORKSPACE_DIR = Path(CONF.paths.workspace_dir)
VOICE_DIR = Path(CONF.paths.voice_dir)
INPUT_DIR = VOICE_DIR / 'input'
OUTPUT_DIR = VOICE_DIR / 'output'
LOG_DIR = VOICE_DIR / 'logs'
LOCK_FILE = VOICE_DIR / '.alberth.lock'

# Asegurar que los directorios existen
'''
new_src = new_src[:start] + replacement + new_src[end:]

# Replace timeouts in subprocess calls
replacements = {
    r'timeout=25': f'timeout={CONF.service_timeouts.stt_cloud}',
    r'timeout=30': f'timeout={CONF.service_timeouts.stt_local}',
    r'timeout=10': f'timeout={CONF.service_timeouts.talamo}',
    r'timeout=15': f'timeout={CONF.service_timeouts.helper}',
    r'timeout=60': f'timeout={CONF.service_timeouts.agent}',
    r'timeout=20': f'timeout={CONF.service_timeouts.tts}',
}
for pattern, repl in replacements.items():
    new_src = re.sub(pattern, repl, new_src)

# Replace CircuitBreaker constructors
cb_patterns = [
    (r"CircuitBreaker\('stt_groq',\s*CircuitBreakerConfig\(failure_threshold=3,\s*recovery_timeout=30,\s*timeout=25\)",
     f"CircuitBreaker('stt_groq', CircuitBreakerConfig(failure_threshold={CONF.circuit_breaker.stt_cloud.failure_threshold}, recovery_timeout={CONF.circuit_breaker.stt_cloud.recovery_timeout}, timeout={CONF.circuit_breaker.stt_cloud.timeout}))"),
    (r"CircuitBreaker\('stt_local',\s*CircuitBreakerConfig\(failure_threshold=3,\s*recovery_timeout=30,\s*timeout=30\)",
     f"CircuitBreaker('stt_local', CircuitBreakerConfig(failure_threshold={CONF.circuit_breaker.stt_local.failure_threshold}, recovery_timeout={CONF.circuit_breaker.stt_local.recovery_timeout}, timeout={CONF.circuit_breaker.stt_local.timeout}))"),
    (r"CircuitBreaker\('albert_agent',\s*CircuitBreakerConfig\(failure_threshold=5,\s*recovery_timeout=30,\s*timeout=60\)",
     f"CircuitBreaker('albert_agent', CircuitBreakerConfig(failure_threshold={CONF.circuit_breaker.agent.failure_threshold}, recovery_timeout={CONF.circuit_breaker.agent.recovery_timeout}, timeout={CONF.circuit_breaker.agent.timeout}))"),
    (r"CircuitBreaker\('tts_pipeline',\s*CircuitBreakerConfig\(failure_threshold=3,\s*recovery_timeout=30,\s*timeout=20\)",
     f"CircuitBreaker('tts_pipeline', CircuitBreakerConfig(failure_threshold={CONF.circuit_breaker.tts.failure_threshold}, recovery_timeout={CONF.circuit_breaker.tts.recovery_timeout}, timeout={CONF.circuit_breaker.tts.timeout}))"),
    (r"CircuitBreaker\('helper_services',\s*CircuitBreakerConfig\(failure_threshold=3,\s*recovery_timeout=30,\s*timeout=15\)",
     f"CircuitBreaker('helper_services', CircuitBreakerConfig(failure_threshold={CONF.circuit_breaker.helper.failure_threshold}, recovery_timeout={CONF.circuit_breaker.helper.recovery_timeout}, timeout={CONF.circuit_breaker.helper.timeout}))"),
]
for pat, repl in cb_patterns:
    new_src = re.sub(pat, repl, new_src)

# Replace TTLCache instantiation
new_src = re.sub(
    r'query_cache = TTLCache\(ttl_seconds=180,\s*maxsize=500\)',
    f'query_cache = TTLCache(ttl_seconds={CONF.cache.ttl_seconds}, maxsize={CONF.cache.maxsize})',
    new_src
)

# Replace metrics port
new_src = re.sub(
    r'METRICS_PORT = int\(os\.environ\.get\(\'ALBERT_METRICS_PORT\', \'9090\'\)\)',
    f'METRICS_PORT = {CONF.metrics.port}',
    new_src
)

# Replace wakeword session timeout
new_src = re.sub(
    r'session_timeout = 45',
    f'session_timeout = {CONF.wakeword.session_timeout}',
    new_src
)

DST.write_text(new_src, encoding='utf-8')
print(f"Updated file written to {DST}")
