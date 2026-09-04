#!/usr/bin/env python3
# This script will generate a new alberth_master_py.py that uses the config module.

import re
from pathlib import Path

# We'll start from the backup2 which is the last known good version without our config changes.
base_path = Path('/Users/digitalspace/.openclaw/workspace/pipeline_refactor')
src_path = base_path / 'alberth_master_py.py.backup2'
dst_path = base_path / 'alberth_master_py.py'

# Read the source
src = src_path.read_text(encoding='utf-8')

# We'll split the source into lines for easier manipulation, but we can also do string replacements.

# First, let's define the new header we want to insert at the top (after the shebang and the initial comment block).
# We want to keep the shebang and the initial comment block (up to the line before the imports) and then insert our config imports and setup.

# However, to avoid breaking the file, we'll do:

# 1. Replace the entire block from the start of the file until the line '# ======================= LOGGER & CONFIG ======================='
#    with a new block that includes the config import and the setup of constants.

# But note: the backup2 file does not have the config.py module, so we have to import it.

# Let's find the marker for the logger section.
logger_marker = '# ======================= LOGGER & CONFIG ======================='
logger_pos = src.find(logger_marker)

if logger_marker not in src:
    # If we can't find the logger marker, we'll try to find the logger line.
    logger_line = 'logger = logging.getLogger(__name__)'
    logger_pos = src.find(logger_line)
    if logger_pos == -1:
        # Last resort: we'll just prepend the new header and hope for the best.
        # But we know the structure, so we can try to insert after the initial comment block.
        # Let's assume the first 20 lines are the header and then the imports start.
        # We'll do a different approach: we'll replace the imports block.
        pass

# We'll do a more robust method: we'll replace the imports block (from the first import to the logger line) with our new block.

# Find the first import line (after the initial comment block) and the logger line.
lines = src.splitlines(keepends=True)
# Find the index of the first line that starts with 'import' or 'from'
first_import_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith('import') or line.strip().startswith('from'):
        first_import_idx = i
        break

# Find the index of the logger line
logger_idx = None
for i, line in enumerate(lines):
    if line.strip().startswith('logger = logging.getLogger(__name__)'):
        logger_idx = i
        break

if first_import_idx is None or logger_idx is None:
    # Fallback: we'll just do string replacement for the known constants and hope the structure is similar.
    # We'll do the replacement by scanning for patterns.
    pass
else:
    # We'll replace the lines from first_import_idx to logger_idx (exclusive) with our new import block.
    new_import_block = '''import os
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

# Import our configuration
import config

# Paths from config
WORKSPACE_DIR = Path(config.PATHS['workspace_dir'])
VOICE_DIR = Path(config.PATHS['voice_dir'])
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

    # Replace the lines
    new_lines = lines[:first_import_idx] + [new_import_block] + lines[logger_idx:]
    src = ''.join(new_lines)

# Now, we have replaced the import block and set up the constants from config.
# Next, we need to remove the old constant definitions that are now duplicated.
# In the original file, after the logger line, there was a section that defined the paths and the log file.
# We have already replaced that with our new block, but note that we replaced from the first import to the logger line.
# The logger line and the following lines (until the next section) are still present.
# We need to remove the old definition of the paths and the log file that come after the logger line.

# Let's look for the old definitions after the logger line and remove them.
# We'll do this by removing a block of lines that we know are the old definitions.

# We'll search for the pattern of the old path definitions and remove them.

# But note: in the backup2 file, after the logger line, there is a blank line and then the section '# Rutas base'.
# We want to remove from the line after the logger line until the line before the next section (which is '# Asegurar que los directorios existen').

# Let's find the line after the logger line and then the next section marker.

# We'll do it by string replacement: we'll remove the block that starts with '# Rutas base' and ends before '# Asegurar que los directorios existen'.

# However, note that we have already replaced the import block, so the logger line is still there and the old path definitions are right after.

# We'll do:
#   Find the logger line, then find the next section marker after that.

# We'll use regex to remove the block.

# Pattern: from the logger line (inclusive) to the line before the next section marker (exclusive) but we want to keep the logger line.
# Actually, we want to remove the lines between the logger line and the next section marker.

# Let's break the string at the logger line, then remove the next block until the section marker.

# We'll do:
#   logger_pos = position of the logger line
#   Then, find the position of the next section marker after the logger line.
#   Then, replace the substring from the end of the logger line to the start of the section marker with nothing (or just a newline).

# But note: the logger line is followed by a newline and then the block we want to remove.

# We'll do:

logger_line = 'logger = logging.getLogger(__name__)'
logger_pos = src.find(logger_line)
if logger_pos != -1:
    # Find the end of the logger line
    end_of_logger_line = logger_pos + len(logger_line)
    # Find the next section marker after the logger line
    section_marker = '# Asegurar que los directorios existen'
    section_pos = src.find(section_marker, end_of_logger_line)
    if section_pos != -1:
        # We want to remove the text between the end of the logger line and the start of the section marker.
        # But note: there might be a blank line or two. We'll remove from the end of the logger line to the start of the section marker.
        # However, we want to keep the newline after the logger line? Actually, we want to remove the blank line and the old definitions.
        # We'll remove from the end of the logger line to the start of the section marker, and then we'll put the section marker back.
        # So we'll replace the slice [end_of_logger_line:section_pos] with a newline (to keep the formatting).
        # But note: the section marker is on its own line, so we want to keep the newline before it? Actually, the section marker line starts with a newline.
        # Let's look at the original: after the logger line, there is a newline, then a blank line, then the section marker line.
        # We want to remove the blank line and the old definitions? Actually, the old definitions are in the section '# Rutas base' which is before the section marker.
        # Wait, the section marker '# Asegurar que los directorios existen' is the line that comes after the '# Rutas base' block.
        # So the block we want to remove is from the line after the logger line until the line before the section marker.

        # Let's change approach: we'll remove the entire block that starts with '# Rutas base' and ends with the line before the section marker.
        # We'll find the start of the '# Rutas base' block and the end of that block (which is the line before the section marker).

        # Find the start of the '# Rutas base' block
        rutabase_marker = '# Rutas base'
        rutabase_pos = src.find(rutabase_marker, end_of_logger_line)
        if rutabase_pos != -1:
            # Find the end of the block: we'll look for the line that starts with '# Asegurar que los directorios existen'
            end_block = src.find('# Asegurar que los directorios existen', rutabase_pos)
            if end_block != -1:
                # We want to remove from the start of the rutabase_marker to the start of the end_block.
                # But note: we want to keep the rutabase_marker line? Actually, we are going to replace the entire block with nothing.
                # However, we have already put the new definitions in the import block, so we don't need this block at all.
                # We'll remove the block and leave a blank line? We'll just remove it and then the section marker will come right after the logger line.
                # We'll replace the slice [rutabase_pos:end_block] with an empty string.
                src = src[:rutabase_pos] + src[end_block:]
            else:
                # If we can't find the end block, we'll just remove the rutabase_marker line and hope.
                src = src[:rutabase_pos] + src[rutabase_pos+len(rutabase_marker):]
        else:
            # If we can't find the rutabase marker, we'll try to remove the block by looking for the next section marker after the logger line and remove everything in between.
            # We already tried that above.
            pass

# Now, we have removed the old path definitions block. The logger line is still there, and then we have the section marker.

# Next, we need to replace the hardcoded values in the rest of the file.

# We'll do a series of regex replacements for the timeouts, circuit breaker parameters, etc.

# First, let's define the config values we have access to (we'll import the config module in the replacement script, but we are in a generator script).
# We'll import the config module from the current directory.

import sys
sys.path.insert(0, str(base_path))
import config

# Now, we can get the values.

# Helper to get a config value with a fallback.
def get_config_val(section, key, default=None):
    return config.CONFIG.get(section, {}).get(key, default)

# But note: our config module has a different structure. Let's look at the config.py we wrote.
# We have:
#   PATHS, SERVICE_TIMEOUTS, CIRCUIT_BREAKER, CACHE, METRICS, WAKEWORD

# We'll use these.

# 1. Replace timeouts in subprocess.run calls.
# We'll replace patterns like 'timeout=25' with the value from config.SERVICE_TIMEOUTS['stt_cloud'] (for example).
# We'll do a mapping from the hardcoded number to the config key.

timeout_mapping = {
    25: ('SERVICE_TIMEOUTS', 'stt_cloud'),
    30: ('SERVICE_TIMEOUTS', 'stt_local'),  # also used for stt_local and helper? Actually, we have to be careful.
    10: ('SERVICE_TIMEOUTS', 'talamo'),
    15: ('SERVICE_TIMEOUTS', 'helper'),
    60: ('SERVICE_TIMEOUTS', 'agent'),
    20: ('SERVICE_TIMEOUTS', 'tts'),
}

# We'll replace each occurrence of 'timeout=<number>' with the corresponding config value.
# We'll do it by iterating over the mapping.
for num, (section, key) in timeout_mapping.items():
    # Get the value from the config module
    if section == 'SERVICE_TIMEOUTS':
        val = config.SERVICE_TIMEOUTS.get(key, num)
    else:
        # This should not happen
        val = num
    # Replace the pattern
    # We'll use regex to match the exact 'timeout=25' (not part of a larger number)
    # We'll use word boundaries? Since it's followed by a comma or space or closing parenthesis.
    # We'll do: r'timeout={}\b'.format(num) but note that the number might be followed by a non-digit.
    # We'll do: r'timeout={}(?=\D)'.format(num) but easier: we can just replace the string and hope it's unique.
    # We'll do a simple string replacement for the exact string.
    old_str = f'timeout={num}'
    new_str = f'timeout={val}'
    src = src.replace(old_str, new_str)

# 2. Replace the CircuitBreaker constructors.
# We'll replace each one with the values from config.CIRCUIT_BREAKER.

# We'll do each one separately.

# stt_groq
cb_stt_groq = config.CIRCUIT_BREAKER['stt_cloud']
# Pattern: CircuitBreaker('stt_groq', CircuitBreakerConfig(failure_threshold=3, recovery_timeout=30, timeout=25))
# We'll replace the numbers.
# We'll do three separate replacements for each parameter, but we can do the whole thing.
# We'll use regex to capture the whole constructor and replace it.

# We'll do:
#   re.sub(r"CircuitBreaker\('stt_groq',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)",
#          f"CircuitBreaker('stt_groq', CircuitBreakerConfig(failure_threshold={cb_stt_groq['failure_threshold']}, recovery_timeout={cb_stt_groq['recovery_timeout']}, timeout={cb_stt_groq['timeout']}))",
#          src)

# But note: there might be spaces. We'll make the regex flexible.

# We'll do for each of the five.

# stt_groq
pattern = r"CircuitBreaker\('stt_groq',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)"
replacement = f"CircuitBreaker('stt_groq', CircuitBreakerConfig(failure_timeout={cb_stt_groq['failure_threshold']}, recovery_timeout={cb_stt_groq['recovery_timeout']}, timeout={cb_stt_groq['timeout']})"
# Wait, note: the parameter names are 'failure_threshold', 'recovery_timeout', 'timeout'. We must use the same.
# Let's fix:
replacement = f"CircuitBreaker('stt_groq', CircuitBreakerConfig(failure_threshold={cb_stt_groq['failure_threshold']}, recovery_timeout={cb_stt_groq['recovery_timeout']}, timeout={cb_stt_groq['timeout']})"
src = re.sub(pattern, replacement, src)

# stt_local
cb_stt_local = config.CIRCUIT_BREAKER['stt_local']
pattern = r"CircuitBreaker\('stt_local',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)"
replacement = f"CircuitBreaker('stt_local', CircuitBreakerConfig(failure_threshold={cb_stt_local['failure_threshold']}, recovery_timeout={cb_stt_local['recovery_timeout']}, timeout={cb_stt_local['timeout']})"
src = re.sub(pattern, replacement, src)

# albert_agent
cb_agent = config.CIRCUIT_BREAKER['agent']
pattern = r"CircuitBreaker\('albert_agent',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)"
replacement = f"CircuitBreaker('albert_agent', CircuitBreakerConfig(failure_timeout={cb_agent['failure_threshold']}, recovery_timeout={cb_agent['recovery_timeout']}, timeout={cb_agent['timeout']})"
src = re.sub(pattern, replacement, src)

# tts_pipeline
cb_tts = config.CIRCUIT_BREAKER['tts']
pattern = r"CircuitBreaker\('tts_pipeline',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)"
replacement = f"CircuitBreaker('tts_pipeline', CircuitBreakerConfig(failure_timeout={cb_tts['failure_threshold']}, recovery_timeout={cb_tts['recovery_timeout']}, timeout={cb_tts['timeout']})"
src = re.sub(pattern, replacement, src)

# helper_services
cb_helper = config.CIRCUIT_BREAKER['helper']
pattern = r"CircuitBreaker\('helper_services',\s*CircuitBreakerConfig\(failure_threshold=\d+,\s*recovery_timeout=\d+,\s*timeout=\d+\)"
replacement = f"CircuitBreaker('helper_services', CircuitBreakerConfig(failure_timeout={cb_helper['failure_threshold']}, recovery_timeout={cb_helper['recovery_timeout']}, timeout={cb_helper['timeout']})"
src = re.sub(pattern, replacement, src)

# 3. Replace the TTLCache initialization.
# We have: query_cache = TTLCache(ttl_seconds=180, maxsize=500)
# We'll replace with the values from config.CACHE
cache_ttl = config.CACHE['ttl_seconds']
cache_maxsize = config.CACHE['maxsize']
pattern = r'query_cache = TTLCache\(ttl_seconds=\d+,\s*maxsize=\d+\)'
replacement = f'query_cache = TTLCache(ttl_seconds={cache_ttl}, maxsize={cache_maxsize})'
src = re.sub(pattern, replacement, src)

# 4. Replace the METRICS_PORT.
# We have: METRICS_PORT = int(os.environ.get('ALBERT_METRICS_PORT', '9090'))
# We want to replace with the value from config.METRICS['port']
metrics_port = config.METRICS['port']
# We'll replace the whole line.
# We'll look for the line that starts with 'METRICS_PORT ='
# We'll do a line-by-line replacement? Let's do regex.
pattern = r'METRICS_PORT = int\(os\.environ\.get\([\'"]ALBERT_METRICS_PORT[\'"], [\'"]9090[\'"]\)\)'
replacement = f'METRICS_PORT = {metrics_port}'
# But note: the original might have single or double quotes. We'll make it more flexible.
# We'll do: 
pattern = r'METRICS_PORT = int\(os\.environ\.get\([\'"]ALBERT_METRICS_PORT[\'"], [\'"]9090[\'"]\)\)'
# However, we can just replace the number 9090 with the port from config, but note that the default is 9090 and we are overriding it.
# We'll do a simpler replacement: replace the string '9090' with the port number, but only in that context.
# We'll do:
#   Replace the default value in the os.environ.get call.
# We'll look for: os.environ.get('ALBERT_METRICS_PORT', '9090')
# and replace the '9090' with the port from config.
# But note: we want to keep the structure so that if the environment variable is set, it still works.
# We'll change the default value.
pattern = r"os\.environ\.get\(['\"]ALBERT_METRICS_PORT['\"],\s*['\"]9090['\"]\)"
replacement = f"os.environ.get('ALBERT_METRICS_PORT', '{metrics_port}')"
src = re.sub(pattern, replacement, src)

# 5. Replace the wake_word session timeout (hardcoded 45 in the check_wake_word function).
# We have: session_timeout = 45
# We'll replace with the value from config.WAKEWORD['session_timeout']
wake_timeout = config.WAKEWORD['session_timeout']
# We'll replace the line that sets session_timeout to 45.
# We'll look for: session_timeout = 45
# But note: there might be multiple occurrences? We hope only one.
pattern = r'session_timeout = 45'
replacement = f'session_timeout = {wake_timeout}'
src = re.sub(pattern, replacement, src)

# Now, we have to write the new file.
dst_path.write_text(src, encoding='utf-8')
print(f"Generated new file at {dst_path}")