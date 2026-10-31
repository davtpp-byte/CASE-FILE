#!/usr/bin/env python3
"""Apply the v0.3.2 code-only update. Never copies/deletes anything in data/."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import shutil
import sys


def fail(message):
    raise SystemExit('Update stopped: ' + message)


def main():
    parser = argparse.ArgumentParser(description='Update Casefile Studio code, preserving projects, uploads and exports in data/. Stop the app first.')
    parser.add_argument('folder', help='Path to your EXISTING casefile-studio installation')
    parser.add_argument('--check', action='store_true', help='Validate only; write nothing')
    args = parser.parse_args()
    source = Path(__file__).resolve().parent
    target = Path(args.folder).expanduser().resolve()
    if not (target / 'app.py').is_file() or not (target / 'data/projects').is_dir():
        fail('Choose the existing app folder containing app.py AND data/projects. This package is not a fresh installation.')
    manifest = json.loads((source / 'manifest.json').read_text())
    entries = manifest['files']
    allowed_roots = {'web', 'tests'}
    checked = []
    # Validate EVERY entry before making any changes or creating a backup.
    for entry in entries:
        rel = Path(entry['path'])
        if rel.is_absolute() or not rel.parts or any(p in ('.', '..') for p in rel.parts):
            fail('Invalid payload path.')
        if len(rel.parts) > 1 and rel.parts[0] not in allowed_roots:
            fail('Unexpected directory; data/, media, exports and credentials are never update targets.')
        if rel.parts[0].lower() in {'data', 'uploads', '.env', '.git', 'qa'}:
            fail('Refusing a protected target.')
        new = (source / 'payload' / rel).resolve()
        dst = (target / rel).resolve()
        if not new.is_relative_to((source / 'payload').resolve()) or not dst.is_relative_to(target):
            fail('A payload/target path escapes its folder, possibly through a symlink.')
        if dst.is_relative_to((target / 'data').resolve()):
            fail('Refusing a target inside data/, including through a symlink.')
        if not new.is_file() or hashlib.sha256(new.read_bytes()).hexdigest() != entry['sha256']:
            fail('Missing or modified payload: ' + str(rel))
        if dst.exists() and not dst.is_file():
            fail('An update target is not a regular file: ' + str(rel))
        checked.append((rel, new, dst))
    print(f'Validated {len(checked)} code/document files for Casefile Studio {manifest["version"]}.')
    print('Projects, uploaded audio/footage, exports and settings in data/ will NOT be touched.')
    if args.check:
        print('Check passed. No files written.')
        return
    backup = target / '.code-backups' / datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
    if not backup.resolve().is_relative_to(target) or backup.resolve().is_relative_to((target / 'data').resolve()):
        fail('The code-backup folder resolves to a protected/external location.')
    backup.mkdir(parents=True)
    written = []
    try:
        for rel, new, dst in checked:
            existed = dst.exists()
            if existed:
                old = backup / rel
                old.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dst, old)
            dst.parent.mkdir(parents=True, exist_ok=True)
            temporary = dst.with_name(dst.name + '.casefile-update.tmp')
            shutil.copy2(new, temporary)
            temporary.replace(dst)
            written.append((rel, dst, existed))
            if rel.as_posix() == 'run.sh':
                dst.chmod(0o755)
    except Exception:
        for rel, dst, existed in reversed(written):
            if existed:
                shutil.copy2(backup / rel, dst)
            else:
                dst.unlink(missing_ok=True)
        raise
    print('Code updated. Previous code is backed up in: ' + str(backup))
    print('Restart the app, then refresh the browser preview. The timestamps panel should show v0.3.2.')


if __name__ == '__main__':
    main()
