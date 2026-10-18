"""Synthetic, one-process-per-stage native OCR probes; never reads score evidence."""

import faulthandler
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys


def emit(stage, **data):
    print(json.dumps({'stage': stage, **data}, default=str), flush=True)


def main(stage):
    faulthandler.enable()
    emit(
        'entry',
        requested=stage,
        machine=platform.machine(),
        packages={
            n: importlib.metadata.version(n) for n in ['paddlepaddle', 'paddleocr', 'paddlex']
        },
        env={k: os.environ.get(k) for k in ['OMP_NUM_THREADS', 'PADDLE_ENABLE_MKLDNN']},
    )
    if stage == 'environment':
        print(Path('/proc/cpuinfo').read_text(), flush=True)
        print(Path('/proc/self/limits').read_text(), flush=True)
        return
    import paddle

    emit(
        'paddle_imported', device=paddle.get_device(), compiled_cuda=paddle.is_compiled_with_cuda()
    )
    if stage == 'tensor':
        a = paddle.to_tensor([[1.0, 2.0], [3.0, 4.0]])
        emit('tensor_result', value=paddle.matmul(a, a).numpy().tolist())
        print(Path('/proc/self/maps').read_text(), flush=True)
        return
    import numpy as np
    from PIL import Image, ImageDraw

    image = Image.new('RGB', (640, 160), 'white')
    ImageDraw.Draw(image).text((40, 50), 'Bb  F  Gm7  Bb/D', fill='black', font_size=32)
    x = np.array(image)
    if stage.startswith('detector'):
        from paddleocr import TextDetection

        emit('before_detector_init')
        model = TextDetection(model_name='PP-OCRv6_medium_det', enable_mkldnn=False)
        emit('detector_initialized')
        if stage == 'detector_predict':
            emit('before_detector_predict')
            emit('detector_returned', result=list(model.predict(x)))
    elif stage == 'recognizer_predict':
        from paddleocr import TextRecognition

        emit('before_recognizer_init')
        model = TextRecognition(model_name='PP-OCRv6_medium_rec', enable_mkldnn=False)
        emit('recognizer_initialized')
        emit('before_recognizer_predict')
        emit('recognizer_returned', result=list(model.predict(x)))
    elif stage == 'pipeline_predict':
        from backend.ocr.paddle_ocr import get_ocr

        emit('before_pipeline_init')
        model = get_ocr()
        emit('pipeline_initialized')
        emit('before_pipeline_predict')
        emit('pipeline_returned', result=list(model.predict(x)))
    elif stage == 'hybrid_predict':
        from backend.ocr.hybrid_detect import detect_chords_hybrid

        image.save('/tmp/synthetic.png')
        emit('before_hybrid')
        emit(
            'hybrid_returned',
            result=detect_chords_hybrid('/tmp/synthetic.png', use_ai_fallback=False),
        )
    else:
        raise ValueError(stage)
    emit('completed')


if __name__ == '__main__':
    main(sys.argv[1])
