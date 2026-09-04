import pathlib, yaml, re, sys
from pathlib import Path

BASE = pathlib.Path('/Users/digitalspace/.openclaw/workspace/pipeline_refactor')
CONFIG_PATH = BASE / 'config.yaml'
SRC = BASE / 'alberth_master_py.py.backup3'  # Use the backup we made before any changes
DST = BASE / 'alberth_master_py.py'

# Load config
with open(CONFIG_PATH, 'rt') as f:
    cfg = yaml.safe_load(f)

# Helper to get nested config
def get_cfg(*keys):
    d = cfg
    for k in keys:
        d = d.get(k, {})
    return d

# Read the source
src = SRC.read_text(encoding='utf-8')

# We'll create a new version by replacing sections.

# 1. Replace the imports and config loading section.
# We want to keep the existing imports but add yaml and pydantic, and then load config.
# However, to avoid complexity, we'll replace from the start of the file until the logger line
# with a new block that includes the config loading.

new_header = '''#!/usr/bin/env python3
# =============================================================================
# ALBERTH MASTER PYTHON REFACTOR - Pipeline de Voz Reescrito en Python
# Versión: 2.1.0 (Refactor con Configuración Externalizada)
# =============================================================================

import os
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
from enum import Enum
from dataclasses import dataclass, field
import yaml
from pydantic import BaseModel, Field, validator

# Load configuration
CONFIG_PATH = Path(__file__).with_name('config.yaml')
if not CONFIG_PATH.is_file():
    raise FileNotFoundError(f"Configuration file not found: {CONFIG_PATH}")
with open(CONFIG_PATH, 'rt', encoding='utf-8') as f:
    raw_cfg = yaml.safe_load(f)

# Pydantic models for validation
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

# Parse and validate config
CONF = AppConfig(**raw_cfg)

# Paths from config
WORKSPACE_DIR = Path(CONF.paths.workspace_dir)
VOICE_DIR = Path(CONF.paths.voice_dir)
INPUT_DIR = VOICE_DIR / 'input'
OUTPUT_DIR = VOICE_DIR / 'output'
LOG_DIR = VOICE_DIR / 'logs'
LOCK_FILE = VOICE_DIR / '.alberth.lock'

# Ensure directories exist
for dir_path in [INPUT_DIR, OUTPUT_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Log file
LOGFILE = LOG_DIR / f'alberth_master_{time.strftime("%Y%m%d")}.log'
'''

# Find where to insert the new header: from start until the line '# ======================= LOGGER & CONFIG ======================='
marker = '# ======================= LOGGER & CONFIG ======================='
pos = src.find(marker)
if pos == -1:
    # Fallback: insert after the initial comment block (first 20 lines)
    # We'll just prepend the new header and keep the rest (might duplicate some imports, but we'll handle)
    # For safety, let's find the first line that is not a shebang or comment.
    lines = src.splitlines(keepends=True)
    i = 0
    while i < len(lines) and (lines[i].startswith('#') or lines[i].startswith('!')):
        i += 1
    # Insert after the initial block
    insert_point = sum(len(lines[j]) for j in range(i))
    new_src = src[:insert_point] + new_header + src[insert_point:]
else:
    # Replace from start to the marker with the new header, then keep from marker onward
    new_src = new_header + src[pos:]

# Now we need to replace the hardcoded values with config values.

# Replace timeout values in subprocess.run calls
# We'll do simple string replacements for the specific timeouts we know.
# Note: we must be careful not to replace other numbers.
# We'll use regex with word boundaries? Since the pattern is 'timeout=XX', we can just replace that.

def replace_timeout(match):
    # match.group(0) is like 'timeout=25'
    num = int(match.group(1))
    # Map to config
    mapping = {
        25: ('stt_cloud', 'service_timeouts'),
        30: ('stt_local', 'service_timeouts'),  # also used for talamo? Actually talamo is 10
        10: ('talamo', 'service_timeouts'),
        15: ('helper', 'service_timeouts'),
        60: ('agent', 'service_timeouts'),
        20: ('tts', 'service_timeouts'),
    }
    if num in mapping:
        key, section = mapping[num]
        val = get_cfg(section, key)
        return f'timeout={val}'
    else:
        # If not in map, return original (should not happen)
        return match.group(0)

new_src = re.sub(r'timeout=(\d+)', replace_timeout, new_src)

# Replace CircuitBreaker constructors
# We'll replace each one individually with values from config.
# Pattern: CircuitBreaker('name', CircuitBreakerConfig(failure_threshold=X, recovery_timeout=Y, timeout=Z))
def replace_cb(match):
    # We'll capture the name and then replace the numbers.
    # But easier: we can just replace the whole string with a new one using config.
    # We'll do it by name in separate steps.
    return match.group(0)  # placeholder

# Instead of complex regex, we'll do simple string replacement for each known CB.
# We know the exact strings from the backup (but they may have been changed by previous steps).
# Let's just replace using the config values.

# stt_groq
cb_stt_groq = get_cfg('circuit_breaker', 'stt_cloud')
new_src = re.sub(
    r"CircuitBreaker\('stt_groq',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)",
    f"CircuitBreaker('stt_groq', CircuitBreakerConfig(failure_threshold={cb_stt_groq['failure_threshold']}, recovery_timeout={cb_stt_groq['recovery_timeout']}, timeout={cb_stt_groq['timeout']})",
    new_src
)

# stt_local
cb_stt_local = get_cfg('circuit_breaker', 'stt_local')
new_src = re.sub(
    r"CircuitBreaker\('stt_local',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)",
    f"CircuitBreaker('stt_local', CircuitBreakerConfig(failure_threshold={cb_stt_local['failure_threshold']}, recovery_timeout={cb_stt_local['recovery_timeout']}, timeout={cb_stt_local['timeout']})",
    new_src
)

# albert_agent
cb_agent = get_cfg('circuit_breaker', 'agent')
new_src = re.sub(
    r"CircuitBreaker\('albert_agent',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)",
    f"CircuitBreaker('albert_agent', CircuitBreakerConfig(failure_threshold={cb_agent['failure_threshold']}, recovery_timeout={cb_agent['recovery_timeout']}, timeout={cb_agent['timeout']})",
    new_src
)

# tts_pipeline
cb_tts = get_cfg('circuit_breaker', 'tts')
new_src = re.sub(
    r"CircuitBreaker\('tts_pipeline',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)",
    f"CircuitBreaker('tts_pipeline', CircuitBreakerConfig(failure_threshold={cb_tts['failure_threshold']}, recovery_timeout={cb_tts['recovery_timeout']}, timeout={cb_tts['timeout']})",
    new_src
)

# helper_services
cb_helper = get_cfg('circuit_breaker', 'helper')
new_src = re.sub(
    r"CircuitBreaker\('helper_services',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)",
    f"CircuitBreaker('helper_services', CircuitBreakerConfig(failure_threshold={cb_helper['failure_threshold']}, recovery_timeout={cb_helper['recovery_timeout']}, timeout={cb_helper['timeout']})",
    new_src
)

# Replace TTLCache initialization
new_src = re.sub(
    r'query_cache = TTLCache\(ttl_seconds=180,\s*maxsize=500\)',
    f'query_cache = TTLCache(ttl_seconds={cfg["cache"]["ttl_seconds"]}, maxsize={cfg["cache"]["maxsize"]})',
    new_src
)

# Replace metrics port
new_src = re.sub(
    r'METRICS_PORT = int\(os\.environ\.get\(\'ALBERT_METRICS_PORT\', \'9090\'\)\)',
    f'METRICS_PORT = {cfg["metrics"]["port"]}',
    new_src
)

# Replace wake_word session timeout (hardcoded 45 in check_wake_word function)
new_src = re.sub(
    r'session_timeout = 45',
    f'session_timeout = {cfg["wakeword"]["session_timeout"]}',
    new_src
)

# Write the new file
DST.write_text(new_src, encoding='utf-8')
print(f"Patched file written to {DST}")
