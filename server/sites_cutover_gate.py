"""Commit-controlled startup gate; no database or operational imports.

This gate controls this deployment only. It does not establish a SQL/Google
writer fence or authorize native production. Keep NORMAL until those separate
cutover prerequisites can be completed and verified.
"""
from pathlib import Path
import json
import os
import re
import sys

MODE_PATH = Path(__file__).with_name('sites_cutover_mode.json')


def deployment_mode():
    try:
        value = json.loads(MODE_PATH.read_text(encoding='utf-8'))
    except (OSError, ValueError) as error:
        raise RuntimeError('Cutover mode is unreadable; business startup stopped') from error
    if not isinstance(value, dict) or set(value) != {'mode', 'cutover_id'}:
        raise RuntimeError('Invalid cutover mode; business startup stopped')
    mode, identity = value['mode'], value['cutover_id']
    if mode == 'NORMAL' and identity is None:
        return value
    if mode == 'ISOLATED_MIGRATION_READS' and isinstance(identity, str) and re.fullmatch(r'seafood-sites-[a-z0-9-]{1,64}', identity):
        return value
    raise RuntimeError('Invalid cutover mode; business startup stopped')


def launch_maintenance_if_requested():
    if deployment_mode()['mode'] == 'NORMAL':
        return
    # Replace the supervisor/API process before it imports any business code.
    # The isolated module never imports this launcher, so there is no exec loop.
    os.execv(sys.executable, [sys.executable, '-m', 'uvicorn',
        'sites_migration_maintenance:app', '--host', '0.0.0.0',
        '--port', os.environ.get('PORT', '8080'), '--workers', '1'])
    raise RuntimeError('Maintenance process replacement unexpectedly returned')


def require_worker_enabled():
    if deployment_mode()['mode'] != 'NORMAL':
        raise SystemExit('Seafood migration maintenance: worker startup disabled')
