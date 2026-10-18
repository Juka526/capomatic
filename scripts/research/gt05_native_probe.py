"""Single-variable synthetic native inference controls; no score inputs."""

import copy
import faulthandler
import importlib.metadata
import json
import os
from pathlib import Path
import resource
import sys


def emit(stage, **values):
    print(json.dumps({'stage': stage, **values}, default=str), flush=True)


def configuration(case):
    common = {'enable_mkldnn': False}
    if case == 'recognizer-cpu1':
        common['cpu_threads'] = 1
    if case.endswith('newir-off'):
        common['engine_config'] = {
            'paddle_static': {
                'run_mode': 'paddle',
                'cpu_threads': 10,
                'enable_cinn': False,
                'enable_new_ir': False,
            }
        }
    return common


def main(case):
    emit(
        'entry',
        case=case,
        env={k: os.environ.get(k) for k in ['OMP_NUM_THREADS', 'PADDLE_ENABLE_MKLDNN']},
        versions={
            n: importlib.metadata.version(n) for n in ['paddlepaddle', 'paddleocr', 'paddlex']
        },
        requested=configuration(case),
    )
    import paddle

    paddle.disable_signal_handler()
    faulthandler.enable(all_threads=True)
    resource.setrlimit(
        resource.RLIMIT_CORE,
        (512 * 1024 * 1024 if case == 'recognizer-baseline-trace' else 0, 512 * 1024 * 1024),
    )
    emit(
        'runtime',
        core_limits=resource.getrlimit(resource.RLIMIT_CORE),
        cpu_device=paddle.get_device(),
    )
    import numpy as np
    from PIL import Image, ImageDraw
    from paddleocr import TextRecognition, TextDetection

    model_class = TextDetection if case.startswith('detector') else TextRecognition
    name = 'PP-OCRv6_medium_det' if case.startswith('detector') else 'PP-OCRv6_medium_rec'
    emit('before_init', model_name=name)
    model = model_class(model_name=name, **configuration(case))
    emit('initialized', model_class=type(model).__name__, attributes=sorted(vars(model)))
    # Dump existing predictor configuration, never mutate it to make a case pass.
    seen = set()

    def inspect_object(obj, path, depth=0):
        if depth > 6 or id(obj) in seen:
            return
        seen.add(id(obj))
        if type(obj).__name__ == 'PaddlePredictorOption':
            emit('effective_predictor_options', path=path, options=str(obj))
        if isinstance(obj, dict):
            items = list(obj.items())
        elif isinstance(obj, (list, tuple)):
            items = list(enumerate(obj))
        elif hasattr(obj, '__dict__') and type(obj).__module__.startswith(('paddlex', 'paddleocr')):
            items = list(vars(obj).items())
        else:
            return
        for key, value in items:
            inspect_object(value, path + '.' + str(key), depth + 1)

    inspect_object(model, 'model')
    im = Image.new('RGB', (640, 160), 'white')
    ImageDraw.Draw(im).text((40, 50), 'Bb  F  Gm7  Bb/D', fill='black', font_size=32)
    array = np.array(im)
    emit(
        'before_predict',
        source_sha256=__import__('hashlib').sha256(array.tobytes()).hexdigest(),
        maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    )

    def trace(frame, event, arg):
        if (
            event == 'call'
            and 'paddlex/inference/models/runners/paddle_static' in frame.f_code.co_filename
        ):
            emit(
                'python_call',
                file=frame.f_code.co_filename,
                line=frame.f_lineno,
                function=frame.f_code.co_name,
            )

    sys.setprofile(trace)
    result = list(model.predict(array))
    sys.setprofile(None)
    emit('returned', result=result, maxrss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


if __name__ == '__main__':
    main(sys.argv[1])
