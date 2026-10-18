from datetime import datetime
from types import SimpleNamespace
import subprocess

import pytest

import gpu_telemetry


def test_capture_multiple_gpus(monkeypatch):
    def run(command, **kwargs):
        assert command == gpu_telemetry.COMMAND
        assert kwargs == dict(capture_output=True, text=True, check=True, timeout=2)
        return SimpleNamespace(stdout='73 %, 12000 MiB, 16384 MiB, NVIDIA A16\n0, 0 MiB, 16384 MiB, NVIDIA A16\n')
    monkeypatch.setattr(gpu_telemetry.subprocess, 'run', run)
    result = gpu_telemetry.capture('spec.after')
    assert result['available'] and result['point'] == 'spec.after'
    assert datetime.fromisoformat(result['timestamp']).utcoffset().total_seconds() == 0
    assert result['gpus'] == [
        dict(utilization_gpu_pct=73, memory_used_mib=12000, memory_total_mib=16384, name='NVIDIA A16'),
        dict(utilization_gpu_pct=0, memory_used_mib=0, memory_total_mib=16384, name='NVIDIA A16')]


@pytest.mark.parametrize('failure', [FileNotFoundError(), PermissionError(),
    subprocess.TimeoutExpired('nvidia-smi', 2), subprocess.CalledProcessError(1, 'nvidia-smi'),
    RuntimeError('private host details')])
def test_capture_unavailable(monkeypatch, failure):
    def run(*args, **kwargs):
        raise failure
    monkeypatch.setattr(gpu_telemetry.subprocess, 'run', run)
    result = gpu_telemetry.capture('build.before')
    assert not result['available'] and result['gpus'] == []
    assert result['note'].startswith('GPU telemetry unavailable:')
    assert 'private host details' not in str(result)


@pytest.mark.parametrize('stdout', ['', 'not csv', 'NaN, 1, 2, GPU', '101, 1, 2, GPU',
                                   '0, -1, 2, GPU', '0, 1, 2, '])
def test_invalid_output(monkeypatch, stdout):
    monkeypatch.setattr(gpu_telemetry.subprocess, 'run', lambda *a, **kw: SimpleNamespace(stdout=stdout))
    assert not gpu_telemetry.capture('spec.before')['available']


def test_unsupported_metric_is_not_zero(monkeypatch):
    monkeypatch.setattr(gpu_telemetry.subprocess, 'run', lambda *a, **kw:
                        SimpleNamespace(stdout='N/A, 100 MiB, 16384 MiB, NVIDIA A16'))
    result = gpu_telemetry.capture('build.after')
    assert result['available']
    assert result['gpus'][0]['utilization_gpu_pct'] is None
