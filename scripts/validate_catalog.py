"""Validate the published catalogue and optionally its matching local audio files."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, help='Root of the matching local audio library')
    args = parser.parse_args()
    catalog = Path(__file__).resolve().parent.parent / 'catalog'
    summary = json.loads((catalog / '00_验证汇总.json').read_text(encoding='utf-8'))
    failures = []
    audio_count = 0
    source_ids = set()
    for album in summary['albums']:
        name = album['folder']
        data = json.loads((catalog / name / '曲目与来源.json').read_text(encoding='utf-8'))
        tracks = data['tracks']
        extras = data['extras']
        good_tracks = [t for t in tracks if t['status'] == 'downloaded_verified']
        good_extras = [t for t in extras if t['status'] == 'downloaded_verified']
        if len(tracks) != album['catalog_tracks']:
            failures.append(f'{name}: catalogue track count mismatch')
        if len(good_tracks) != album['main_downloaded'] or len(good_extras) != album['extra_downloaded']:
            failures.append(f'{name}: downloaded count mismatch')
        if [t['number'] for t in tracks] != list(range(1, len(tracks) + 1)):
            failures.append(f'{name}: catalogue track order mismatch')
        for track in good_tracks + good_extras:
            audio_count += 1
            source_ids.add(track['video_id'])
            if not all(track['validation'].values()):
                failures.append(f'{name}: failed recorded validation for {track["title"]}')
            if track['url'] != 'https://www.youtube.com/watch?v=' + track['video_id']:
                failures.append(f'{name}: inconsistent source URL for {track["title"]}')
            if args.library is not None:
                path = args.library / name / track['filename']
                if not path.is_file():
                    failures.append(f'Missing local file: {path}')
                    continue
                with path.open('rb') as stream:
                    digest = hashlib.file_digest(stream, 'sha256').hexdigest()
                if digest != track['sha256']:
                    failures.append(f'Checksum mismatch: {path}')
    if audio_count != summary['verified_audio_files']:
        failures.append('Total verified audio file count mismatch')
    result = {
        'albums': len(summary['albums']),
        'verified_audio_records': audio_count,
        'unique_source_videos': len(source_ids),
        'listed_issues': len(summary['issues']),
        'local_files_checked': args.library is not None,
        'passed': not failures,
        'failures': failures,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if failures else 0)


if __name__ == '__main__':
    main()
