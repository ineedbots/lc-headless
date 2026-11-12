"""Prepare recorded issue-32 fixtures for a fresh isolated revision-289 engine.

Run from the repository root. See docs/validation/issue32/README.md for
engine isolation and execution. This command only prepares client files.
"""
import argparse
import json
from pathlib import Path
import secrets
import shutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True,
                        help='scratch JSON template containing local engine RSA/cache settings')
    parser.add_argument('--output', type=Path, required=True, help='new scratch directory')
    parser.add_argument('--case', action='append', help='recorded case to prepare; defaults to all')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    evidence = root / 'docs/validation/issue32'
    fixtures = json.loads((evidence / 'fixtures.json').read_text(encoding='utf-8'))
    selected = args.case or list(fixtures)
    if any(case not in fixtures for case in selected):
        parser.error('unknown case; choose from ' + ', '.join(fixtures))
    template = json.loads(args.config.read_text(encoding='utf-8'))
    output = args.output.resolve()
    if output.exists():
        parser.error('output already exists; choose a new directory and empty isolated engine saves')
    for case in selected:
        folder = output / case
        scripts = folder / 'scripts'
        accounts = folder / 'accounts'
        accounts.mkdir(parents=True)
        scripts.mkdir()
        shutil.copytree(root / 'scripts/bots', scripts / 'bots')
        config = json.loads(json.dumps(template))
        config['server'] = {'host': '127.0.0.1', 'transport': 'tcp', 'port': 43632}
        config['client']['logFile'] = str(folder / 'client.log')
        config['scripting'].update(scriptsDirectory=str(scripts), accountsDirectory=str(accounts),
                                   progressDirectory=str(folder / 'progress'), connectAttempts=0,
                                   loginIntervalSeconds=2)
        write(folder / 'client.json', config)
        for index, participant in enumerate(fixtures[case]):
            account = participant['account']
            account['password'] = secrets.token_hex(8)
            shutil.copyfile(evidence / 'harnesses' / participant['harness'],
                            scripts / account['script']['file'])
            write(accounts / f'{index}.jsonc', account)
    print(f'Prepared {len(selected)} cases in {output}')


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
