#!/usr/bin/env python3
# Configuration module for Alberth Master
# Loads settings from config.yaml and provides them as module-level variables.

import yaml
import os
from pathlib import Path

# Load configuration from YAML file
CONFIG_PATH = Path(__file__).with_name('config.yaml')
with open(CONFIG_PATH, 'rt', encoding='utf-8') as f:
    _config = yaml.safe_load(f)

# Helper to get nested config values with dot notation (e.g., get_config('service_timeouts', 'stt_cloud'))
def get_config(*keys, default=None):
    """Get a nested configuration value."""
    d = _config
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return default
    return d

# --- Paths ---
PATHS = get_config('paths')
WORKSPACE_DIR = Path(PATHS['workspace_dir'])
VOICE_DIR = Path(PATHS['voice_dir'])
INPUT_DIR = VOICE_DIR / 'input'
OUTPUT_DIR = VOICE_DIR / 'output'
LOG_DIR = VOICE_DIR / 'logs'
LOCK_FILE = VOICE_DIR / '.alberth.lock'

# Ensure directories exist
for dir_path in [INPUT_DIR, OUTPUT_DIR, LOG_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Log file
LOGFILE = LOG_DIR / f'alberth_master_{__import__("time").strftime("%Y%m%d")}.log'

# --- Service Timeouts ---
SERVICE_TIMEOUTS = get_config('service_timeouts')
# Example usage: SERVICE_TIMEOUTS['stt_cloud']

# --- Circuit Breaker Configs ---
CIRCUIT_BREAKER = get_config('circuit_breaker')
# Example usage: CIRCUIT_BREAKER['stt_cloud'] -> {'failure_timeout': 3, 'recovery_timeout': 30, 'timeout': 25}

# --- Cache ---
CACHE = get_config('cache')

# --- Metrics ---
METRICS = get_config('metrics')
METRICS_PORT = METRICS['port']

# --- Wake Word ---
WAKEWORD = get_config('wakeword')
WAKEWORD_ENABLED = WAKEWORD['enabled']
WAKEWORD_SESSION_TIMEOUT = WAKEWORD['session_timeout']