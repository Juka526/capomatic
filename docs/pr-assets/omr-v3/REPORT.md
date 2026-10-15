# Capomatic V3 악보 인식·조옮김 정확도 보고서

- 평가 커밋: `5bccb15` (CI 실행 [38793542488](https://github.com/Juka526/capomatic/actions/runs/38793542488), GitHub Actions `ubuntu-latest` 4 vCPU / 16 GB, 운영 Docker 이미지 안에서 실행)
- 도구: Audiveris 5.11.0 (커밋 `7a36078`), PaddleOCR 3.7.0 (V1과 같은 v6-medium 검출 모델), music21 9.9.1, MuseScore 3, Tesseract 4.1.0 데이터
- 재현: `python -m scripts.omr_v3.evaluate --out <dir>` (Docker 이미지 안), 보고서는 `python -m scripts.omr_v3.report <dir>`

## 결론

- **고해상도 PDF 3곡 (300 dpi, 개발용):** 음표 99.2%(620개 중 615개, 음높이+길이 모두 일치), 코드 재현율 94.2%·정밀도 97.0%, 조표·박자표 100%. 99% 목표는 **음표에서만** 넘었고 코드는 넘지 못했다.
- **저해상도 JPEG 1곡 (745 px, 블라인드 평가용):** 음표 77.8%, 코드 재현율 81.0%·정밀도 90.4%. 반복 기호(volta, D.S.)도 사라져 **연주에 바로 쓸 수 없다**. 이런 입력에는 이제 `low_resolution_input` 경고가 붙는다.
- **조옮김·카포 변환 자체는 정확했다.** 결과 악보를 따로 조옮김한 정답과 비교했을 때 점수가 인식 정확도와 같았다. 즉 오류는 모두 인식 단계에서 생겼고 조옮김에서 새로 생긴 오류는 0건이다. MuseScore가 PDF를 만들 때 읽은 내용도 입력 MusicXML과 100% 같았다.
- **가사:** 1절 글자 정확도 45–56%. 별도 지표로만 보고하며 신뢰할 수 없다.
- **처리 시간:** 페이지당 43–60초 (API 실측 p50 43.7초). **30초 목표는 달성하지 못했다.** 대부분이 Audiveris 시간이다(41–59초).

**완성 여부:** 깨끗한 300 dpi 악보에서는 음표가 정답과 거의 일치한다. 다만 한 곡(주님 난 알고 싶어요)에서 워터마크 때문에 한 마디가 틀렸고, 코드도 5–6%가 빠지거나 틀린다. 그래서 "사람이 확인하는 전제의 실험 기능" 수준이며, 검토 없이 쓰는 제품 수준은 아니다.

## 평가 방법

1. **정답 기준 (`tests/omr_v3_eval/reference/*.gt`):** 원본 악보를 300 dpi로 잘라 확대해 보면서 마디마다 손으로 옮겨 적었다. 마디 길이 합계는 스크립트가 자동 검사한다. Audiveris와 결과가 다른 곳은 모두 원본 이미지를 다시 확대해 확인했다. 이 과정에서 정답 쪽 실수 2건(친구여 6·14마디 리듬, 자유 27마디 D5)을 찾아 고쳤다. 기록이 git 히스토리에 남아 있다.
2. **블라인드 평가:** 개발 중에 오류를 보고 보정을 만든 곡은 3곡(dev)이다. `naui`(나의 모습 나의 소유)는 보정 튜닝에 쓰지 않았다. 단, 이 곡의 레이아웃(코드명이 음표 위 가운데 정렬)을 본 뒤 정렬 방식 자동 선택을 추가했다. 정확도 수치를 보고 튜닝한 것은 아니다.
3. **조옮김 정답:** 파이프라인 코드를 쓰지 않고 따로 만든다. 음표는 music21의 `transpose`에 음정 이름을 직접 지정하고, 코드는 V1의 `transpose_chord`로 옮긴다.
4. **지표:**
   - 음표/쉼표는 편집거리로 정렬한 뒤 음높이와 길이가 모두 맞으면 정답이다.
   - 코드는 같은 마디, ½박 이내, 같은 표기여야 정답이다.
   - 조표·박자표는 마디별로 비교한다.
   - 가사는 1절 한글 글자의 편집거리로 계산한다.

## 결과 (변환된 MusicXML vs 독립적으로 조옮김한 정답)

| Sheet | Set | Condition | Notes exact | Pitch | Rhythm | Chords R / P | Key sig | Time sig | Lyrics v1 | MuseScore fidelity | Time (s) | Tool peak RSS |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| jusim | dev | key+2 (cold) | 97.1% | 98.3% | 97.5% | 86.8% / 97.1% | 100.0% | 100.0% | 44.7% | 100.0% | 52.9 | 1091 MB |
| jusim | dev | capo-2 | 97.1% | 98.3% | 97.5% | 86.8% / 97.1% | 100.0% | 100.0% | 44.7% | 100.0% | 50.1 | 1146 MB |
| jayu | dev | key-2 | 100.0% | 100.0% | 100.0% | 98.4% / 98.4% | 100.0% | 100.0% | 50.5% | 100.0% | 54.4 | 1157 MB |
| jayu | dev | capo-3 | 100.0% | 100.0% | 100.0% | 98.4% / 98.4% | 100.0% | 100.0% | 50.5% | 100.0% | 54.1 | 1163 MB |
| chingu | dev | key+2 | 100.0% | 100.0% | 100.0% | 94.4% / 94.4% | 100.0% | 100.0% | 55.5% | 100.0% | 42.8 | 1188 MB |
| chingu | dev | capo-2 | 100.0% | 100.0% | 100.0% | 94.4% / 94.4% | 100.0% | 100.0% | 55.5% | 100.0% | 43.0 | 1201 MB |
| naui | held-out | key-2 | 77.8% | 86.9% | 79.1% | 81.0% / 90.4% | 93.8% | 96.9% | 53.2% | 100.0% | 60.2 | 1339 MB |
| naui | held-out | capo-2 | 77.8% | 86.9% | 79.1% | 81.0% / 90.4% | 93.8% | 96.9% | 53.2% | 100.0% | 59.0 | 1351 MB |

**dev pooled (key-change runs, transposed output vs independently transposed reference):** notes exact 99.2% of 620 notes, pitch 99.5%; chords recall 94.2%, precision 97.0% of 138 chords.

**held-out pooled (key-change runs, transposed output vs independently transposed reference):** notes exact 77.8% of 153 notes, pitch 86.9%; chords recall 81.0%, precision 90.4% of 58 chords.

Chord source comparison (key-change runs):

| Sheet | Audiveris chords R / P | PaddleOCR + Audiveris R / P |
|---|---|---|
| jusim | 65.8% / 100.0% | 86.8% / 97.1% |
| jayu | 59.4% / 97.4% | 98.4% / 98.4% |
| chingu | 63.9% / 95.8% | 94.4% / 94.4% |
| naui | 37.9% / 95.7% | 81.0% / 90.4% |

`Notes exact`·`Pitch`는 쉼표를 뺀 음표 기준, `Rhythm`은 쉼표를 포함한 길이 기준. `capo`는 음표가 바뀌지 않아야 하므로 key 결과와 같은 것이 정상이다.
측정된 Python 프로세스 최대 RSS(PaddleOCR 모델 포함)는 1.09–1.35 GB이고, 로컬에서 따로 잰 Audiveris 단독 RSS는 0.76–0.94 GB였다. 컨테이너 상주 메모리는 변환 후 약 660 MiB였다(`api-container-stats.txt`).
처리 시간은 러너에 따라 달랐다. 같은 코드로 이전에 실행했을 때는 PaddleOCR이 Audiveris와 CPU를 다투면서 71–97초가 걸렸다(커밋 `672da58`).

## 시각 검사 (side_by_side_*.jpg)

모든 결과 PDF를 원본 옆에 놓고 직접 확인했다. 검사 중에 발견해서 고친 문제는 다음과 같다. 숫자는 고친 뒤의 것이다.

| 발견한 문제 | 원인 | 조치 |
|---|---|---|
| 워터마크 때문에 생긴 2성부 온쉼표 | WCT 워터마크를 쉼표로 인식 | 쉼표만 있는 성부 제거 |
| p, mf, sf, 악센트, 페르마타가 곳곳에 찍힘 | 워터마크와 가사 하이픈을 기호로 인식 | 셈여림·아티큘레이션·페르마타 제거 (`CAPOMATIC_OMR_KEEP_MARKS=1`이면 유지) |
| 가온 C(덧줄)를 D4로 읽음 (자유, 5개) | 붙어 있는 덧줄 조각을 놓침 | 픽셀로 덧줄 확인 후 보정. 자유의 음높이 97.6% → 100% |
| `Cadd2`, `C7sus4`, `Dm7(11)`가 `C`, `Dm`으로 출력됨 | MuseScore가 kind@text를 무시함 | MusicXML `<degree>`로 기록 (전체 코드 팔레트로 확인) |
| `Am7/c`가 조옮김되지 않고 그대로 출력됨 | Audiveris가 코드를 글자로 내보냄 | 코드 형태의 글자를 코드 기호로 변환하고, 읽을 수 없는 것은 삭제 후 보고 |
| 다장조 곡을 D로 옮겼는데 조표가 없음 | C장조는 `<key>`가 생략됨 | 첫 마디에 조표를 명시한 뒤 조옮김 |
| "Music21 Fragment" 제목, 쪽 절반이 빈 2쪽 PDF, "0"·마디번호 잔재 | 원본 레이아웃과 credit을 그대로 사용 | 레이아웃 정보 제거, 제목·작곡자만 메타데이터로 남김 |
| 블라인드 곡의 코드가 반영되지 않음 (37.9%) | 조 바뀜 때문에 22마디가 두 덩어리로 나뉨 | Audiveris 마디 id로 매핑. 81.0%로 개선 |
| 컨테이너에서 Audiveris가 매번 실패 | GTK HiDPI 검사에서 `UnsatisfiedLinkError` 발생 | `sun.java2d.uiScale`/`GDK_SCALE` 설정 |

## 남은 오류 (실패 사례)

- **주님 난 알고 싶어요 9마디:** 워터마크 "W" 획이 지나가는 자리의 8분·16분 음표 3개가 빠지고 그 뒤 리듬이 밀렸다. 마디 길이 합계는 맞아서 경고에도 잡히지 않았다.
- **코드 OCR:**
  - 겹쳐 붙은 `B♭add2 B♭m6`의 일부를 놓쳤다(주님 4·8·16마디).
  - 위첨자 `7(11)`을 놓쳐 `Dm`으로 읽었다(친구여 2·10마디).
  - 저해상도에서 `D/F♯`의 ♯를 놓쳐 `D/F`로 읽었고, 조옮김하면 `C/E♭`이 된다(naui 6·7·16마디). **잘못된 코드가 그럴듯하게 출력되므로 위험하다.**
- **저해상도 JPEG (naui):**
  - 47개 음표/쉼표가 다르다.
  - 1·2번 volta, D.S., 반복 구조가 사라졌다.
  - 2/4 마디 앞뒤의 박자가 어긋났다.
  - 마디 길이 경고 다수가 보고서에 남는다.
- **가사:** 음절 단위가 아니라 단어 덩어리로 붙고, 글자 정확도는 약 50%이다.
- **표기 차이:** `Dm7(11)`은 `Dm7add11`로, `G2`는 `Gadd2`로 표시된다. 의미는 같다.

## 기존 기능 회귀

- `python -m pytest`: main 기준 609 passed / 11 skipped, 이 브랜치 694 passed / 11 skipped (V3 테스트 85개 추가). 기존 테스트는 모두 통과한다.
- CI `docker` 작업: 통합 이미지에서 ♭/♯ 글리프, `/health`, 실제 `/detect`(친구야.jpeg 코드 검출)가 모두 통과한다. V1 코드 인식과 카포 렌더는 바뀌지 않았다.
- `frontend`: node 테스트 47개, `tsc`, `next build` 통과. Vercel preview 빌드도 Ready.

## 상세 차이 목록 (인식 결과 vs 정답, 조옮김 전)


<details><summary><b>jusim</b>: 6 note/rest differences, 5 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 9 | 1 | A4/1/2 | (missing) |
| 9 | 3/2 | G4/1/4 | (missing) |
| 9 | 7/4 | A4/1/4 | (missing) |
| 9 | 3 | rest/1/2 | G4/1/2 |
| 9 | 7/2 | A4/1/4 | A4/1/2 |
| 9 | 15/4 | A4/1/4 | A4/1 |

| Bar (ref) | Beat | Expected chord | Chords found in that bar |
|---|---|---|---|
| 4 | 0 | Bbadd2 | Bbm6@2 |
| 8 | 0 | Bbadd2 | Bbm6@3 |
| 8 | 2 | Bbm6 | Bbm6@3 |
| 16 | 0 | Bbadd2 | – |
| 16 | 2 | Bbm6 | – |

</details>

<details><summary><b>jayu</b>: 0 note/rest differences, 1 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected chord | Chords found in that bar |
|---|---|---|---|
| 18 | 0 | A7/C# | A@0, Dm7@2 |

</details>

<details><summary><b>chingu</b>: 0 note/rest differences, 2 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected chord | Chords found in that bar |
|---|---|---|---|
| 2 | 2 | Dm711 | C@0, Dm@2 |
| 10 | 2 | Dm711 | C@0, Dm@2 |

</details>

<details><summary><b>naui</b>: 47 note/rest differences, 11 missed or wrong chords</summary>

| Bar (ref) | Beat | Expected | Found |
|---|---|---|---|
| 2 | 0 | B3/1/2 | B3/1 |
| 2 | 1/2 | G4/1/2 | E5/1 |
| 2 | 2 | G4/3/2 | G4/1 |
| 2 | 7/2 | rest/1/2 | E4/1/2 |
| 3 | 0 | E4/1/2 | G4/1/2 |
| 7 | 1/2 | C#4/1/2 | C#4/3/4 |
| 7 | 3/2 | A3/1/2 | C#4/3/2 |
| 7 | 2 | A3/1 | C#4/3/4 |
| 7 | 3 | A3/1/2 | D4/1/2 |
| 8 | 0 | D4/1/2 | C#4/3/4 |
| 9 | 0 | (extra) | E5/2 |
| 9 | 0 | E4/3 | E4/2 |
| 9 | 3 | rest/1 | F#4/1 |
| 10 | 0 | F#4/1 | E4/1 |
| 11 | 3/2 | rest/1/2 | (missing) |
| 12 | 7/2 | rest/1/2 | (missing) |
| 16 | 1 | B3/1/2 | B3/1 |
| 16 | 3/2 | E4/1/2 | C#5/1 |
| 16 | 2 | D4/3/2 | D4/1 |
| 16 | 7/2 | rest/1/2 | B3/1/2 |
| 17 | 0 | B3/1/2 | D4/1/2 |
| 22 | 0 | A4/7/2 | A4/2 |
| 22 | 7/2 | rest/1/2 | (missing) |
| 23 | 3 | rest/1/2 | (missing) |
| 24 | 3 | rest/1/2 | C4/1 |
| 25 | 0 | A4/1/2 | (missing) |
| 25 | 1/2 | A4/1/2 | (missing) |
| 25 | 1 | A4/1/2 | (missing) |
| 25 | 3/2 | G4/1/2 | (missing) |
| 25 | 2 | G4/1/2 | (missing) |
| 25 | 5/2 | E4/1/2 | (missing) |
| 25 | 3 | E4/1/2 | (missing) |
| 25 | 7/2 | D4/1/2 | (missing) |
| 26 | 7/2 | rest/1/2 | (missing) |
| 27 | 2 | G4/1/2 | G4/1 |
| 27 | 5/2 | E4/1/2 | E4/1 |
| 27 | 3 | D4/1/2 | (missing) |
| 27 | 7/2 | C4/1/2 | (missing) |
| 28 | 0 | C4/1 | C4/3/2 |
| 28 | 7/2 | D4/1/2 | (missing) |
| 29 | 5/2 | C4/1/2 | C4/3/4 |
| 29 | 3 | A4/1 | A4/3/4 |
| 30 | 0 | G4/7/2 | G4/2 |
| 29 | 2 | (extra) | A4/1/4 |
| 30 | 0 | (extra) | E5/2 |
| 30 | 2 | (extra) | D4/2 |
| 32 | 0 | D4/4 | D4/2 |

| Bar (ref) | Beat | Expected chord | Chords found in that bar |
|---|---|---|---|
| 6 | 3 | D/F# | G2@0, D/F@3 |
| 7 | 2 | D/F# | Em7@0, D/F@7/4 |
| 9 | 0 | Em7/A | Em7/A@2 |
| 9 | 3 | A | Em7/A@2 |
| 16 | 2 | D/F# | Em9@0, D/F@3 |
| 20 | 3 | G/D | D@0, A/D@2 |
| 21 | 2 | A/D | D@0 |
| 21 | 3 | G/D | D@0 |
| 25 | 0 | Gm9 | Am7@0, Dm@2 |
| 25 | 2 | C | Am7@0, Dm@2 |
| 31 | 0 | D | – |

</details>

