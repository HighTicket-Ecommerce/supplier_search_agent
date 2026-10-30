"""Best-effort provenance for offline benchmark helpers."""
import subprocess


def git_commit(root):
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def git_comparison(root, baseline_ref, paths=('backend', 'ui')):
    result = {'baseline_ref': baseline_ref, 'baseline_commit': None, 'code_commit': git_commit(root),
              'status': 'unavailable', 'changed': None}
    try:
        baseline = subprocess.check_output(['git', 'merge-base', 'HEAD', baseline_ref], cwd=root,
                                           text=True, stderr=subprocess.DEVNULL).strip()
        diff = subprocess.check_output(['git', 'diff', baseline, 'HEAD', '--', *paths], cwd=root,
                                       text=True, stderr=subprocess.DEVNULL)
        result.update(baseline_commit=baseline, status='available', changed=bool(diff))
    except (OSError, subprocess.CalledProcessError):
        pass
    return result
