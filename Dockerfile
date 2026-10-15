# ---------------------------------------------------------------------------
# V3 score conversion tools (experimental; routes are off unless
# CAPOMATIC_ENABLE_OMR_V3=1). Built in side stages so the runtime image only
# receives the finished artefacts.
# ---------------------------------------------------------------------------

# Audiveris (AGPL-3.0) from a pinned commit. 5.9.0, the latest tag, still
# resolves ImageJ/JAI from the JBoss repository; this development commit
# (Implementation-Version 5.11.0) builds from Maven Central. jai-core is not used
# by the code (only a system-property name), so it is dropped from the build.
FROM eclipse-temurin:25-jdk AS audiveris
ARG AUDIVERIS_COMMIT=7a36078e7ba0c006052c1f661b949cf9b729f505
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN git init -q audiveris && cd audiveris && \
    git remote add origin https://github.com/Audiveris/audiveris.git && \
    git fetch -q --depth 1 origin "${AUDIVERIS_COMMIT}" && git checkout -q FETCH_HEAD && \
    sed -i '/"javax.media:jai-core:1.1.3",/d' app/build.gradle && \
    ./gradlew --no-daemon -q :app:installDist && \
    mv app/build/install/app /opt/audiveris

# Tesseract 4.1.0 language data with the legacy engine Audiveris requires
# (Debian's tessdata packages are LSTM-only and fail Audiveris' OCR init).
FROM debian:bookworm-slim AS tessdata
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl && rm -rf /var/lib/apt/lists/*
WORKDIR /opt/tessdata
RUN for lang in eng kor osd; do \
      curl -fsSL -o "$lang.traineddata" "https://raw.githubusercontent.com/tesseract-ocr/tessdata/4.1.0/$lang.traineddata"; \
    done && printf '%s\n' \
      'daa0c97d651c19fba3b25e81317cd697e9908c8208090c94c3905381c23fc047  eng.traineddata' \
      '9520bfe9e3cfc38d4a808e036b0287c88a1d37fb80b9a0a23928ddccdd20595b  kor.traineddata' \
      'e19f2ae860792fdf372cf48d8ce70ae5da3c4052962fe22e9de1f680c374bb0e  osd.traineddata' \
    | sha256sum -c -

FROM eclipse-temurin:25-jre AS jre

FROM python:3.12-slim

# Runtime libraries: libgl1/libglib2.0-0 for OpenCV, libgomp1 (OpenMP) for
# paddlepaddle's libpaddle.so. The pre-V1 image got libgomp1 only as a side
# effect of installing gcc; without it every /detect fails to import paddle.
# fonts-dejavu-core gives the renderer a font with ♭/♯ glyphs (DejaVu Sans);
# without it Pillow's built-in font draws accidentals as ASCII b/#.
# V3: poppler-utils (pdfinfo/pdftoppm), musescore3 (MusicXML -> PDF, GPL-2.0 with
# font exceptions) and fonts-nanum so Korean lyrics and titles render.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 fonts-dejavu-core \
    poppler-utils musescore3 fonts-nanum && \
    rm -rf /var/lib/apt/lists/*

COPY --from=jre /opt/java/openjdk /opt/java/openjdk
COPY --from=audiveris /opt/audiveris /opt/audiveris
COPY --from=tessdata /opt/tessdata /opt/tessdata

WORKDIR /app

# v6-medium matches production and regressed 0/16 canonical sheets against the
# frozen production baseline in the CI canary (mobile: 11/16). See #9 and #4.
ENV CHORDTAYLOR_OCR_DET_MODEL=v6-medium \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    PADDLE_MAX_STITCHED_PIXELS=900000 \
    PADDLE_STITCH_MAX_SAFE_PIXELS=900000 \
    PADDLE_MIN_STITCH_RESIZE_SCALE=0.85 \
    RENDER_USE_INPAINT=0 \
    JAVA_HOME=/opt/java/openjdk \
    TESSDATA_PREFIX=/opt/tessdata \
    CAPOMATIC_AUDIVERIS_BIN=/opt/audiveris/bin/Audiveris \
    CAPOMATIC_MUSESCORE_BIN=mscore3 \
    CAPOMATIC_ENABLE_OMR_V3=0

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860
CMD ["sh", "-c", "exec uvicorn backend.api.main:app --host 0.0.0.0 --port \"${PORT:-7860}\""]
