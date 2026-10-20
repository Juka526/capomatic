"""Argument-array subprocess execution with deadline and process-group teardown."""
import asyncio
import contextlib
import os
import signal
import time


class ProcessFailure(RuntimeError):
    pass


async def execute(argv, cwd, timeout, env=None, stdin=None, control=None, max_output=2_000_000, on_spawn=None):
    if timeout <= 0:
        raise ProcessFailure('deadline exhausted before spawn')
    started = time.time()
    proc = await asyncio.create_subprocess_exec(
        *map(str, argv), cwd=cwd, env=env, stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, start_new_session=True)
    if on_spawn:
        try:
            on_spawn(proc.pid)
        except BaseException:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
            await proc.wait()
            raise
    output = [bytearray(), bytearray()]

    async def drain(stream, index):
        while chunk := await stream.read(8192):
            output[index].extend(chunk)
            if sum(map(len, output)) > max_output:
                raise ProcessFailure('process output limit exceeded')

    async def watch():
        while proc.returncode is None:
            if control and control() != 'RUN':
                raise ProcessFailure('owner paused or stopped the run')
            await asyncio.sleep(0.1)

    jobs = [asyncio.create_task(drain(proc.stdout, 0)), asyncio.create_task(drain(proc.stderr, 1)),
            asyncio.create_task(watch())]
    try:
        if stdin:
            proc.stdin.write(stdin.encode())
            await proc.stdin.drain()
        proc.stdin.close()
        async def collect():
            await asyncio.gather(proc.wait(), *jobs)
        await asyncio.wait_for(collect(), timeout)
    except BaseException as exc:
        if proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                os.killpg(proc.pid, signal.SIGKILL)
        await proc.wait()
        for job in jobs:
            job.cancel()
        await asyncio.gather(*jobs, return_exceptions=True)
        exc.process_evidence = {'pid': proc.pid, 'exit_code': proc.returncode,
            'stdout': output[0].decode(errors='replace'), 'stderr': output[1].decode(errors='replace'),
            'started': started, 'finished': time.time(), 'error_type': type(exc).__name__}
        raise
    result = {'pid': proc.pid, 'argv': list(map(str, argv)), 'exit_code': proc.returncode,
              'stdout': output[0].decode(errors='replace'), 'stderr': output[1].decode(errors='replace'),
              'started': started, 'finished': time.time()}
    return result
