export type Lang = 'ko' | 'en';

export const translations = {
  ko: {
    // Nav
    myJobs: '내 작업',
    login: '로그인',
    logout: '로그아웃',

    // Hero
    subtitle: '키를 선택하세요',
    heroHeadline: '코드 악보를 바로 전조하세요',
    heroSubcopy: '',
    heroTrust: 'PNG · JPG · 가입 없이 사용',
    heroPrimaryCta: '악보 업로드',

    // Upload
    uploadSheet: '악보 업로드',
    changeSheet: '악보 변경',
    detectingChords: '코드 감지 중…',
    detectedKey: '감지된 키:',
    uploadFirst: '먼저 악보를 업로드하세요',
    onlyPngJpg: 'PNG, JPG 파일만 지원됩니다.',
    fileTooLarge: '파일 크기가 20MB를 초과합니다.',
    uploadTooLarge: '이미지 크기나 해상도가 허용 범위를 초과합니다. 20MB 이하, 5천만 픽셀 이하의 이미지를 사용하세요.',
    invalidUpload: '이미지를 처리할 수 없습니다. 손상되지 않은 정적 PNG 또는 JPEG 이미지를 선택하세요.',
    ocrBusy: '현재 악보 감지 요청이 많습니다. 잠시 후 다시 시도하세요.',
    detectionExpired: '이전 감지 결과가 만료되었습니다. 악보를 다시 업로드하세요.',
    failedConnect: '서버에 연결할 수 없습니다.',
    closeMenu: '메뉴 닫기',
    transposeDown: '반음 내리기',
    transposeUp: '반음 올리기',
    capoSelector: '카포 프렛 선택',
    selectCapoFret: (n: number) => `카포 ${n}프렛 선택`,

    // Fretboard
    capo: '카포',
    none: '없음',
    fret: '프렛',
    open: '오픈',
    capoPosition: '카포 위치',
    transposeUpInfo: (n: number) => `+${n} 반음`,

    // Options
    rendering: '렌더링 중…',
    updating: '업데이트 중…',

    // Result
    replace: '교체',
    above: '위에',
    viewOriginal: '원본 보기',
    viewRendered: '결과 보기',
    downloadPng: 'PNG 다운로드',
    longPressToSave: '이미지를 길게 눌러 저장하세요',
    saveImageTitle: '전조한 악보 이미지',
    closeDialog: '닫기',
    originalSheetAlt: '업로드한 원본 코드 악보',
    renderedSheetAlt: (mode: string) => `${mode === 'replace' ? '교체' : '위에 표시'} 방식으로 전조한 코드 악보`,

    // Empty state
    uploadYourScore: '악보를 업로드하세요',
    uploadCta: '악보 이미지 업로드하기',
    uploadHint: 'PNG · JPG 지원 · 최대 20MB',
    workflowStepUpload: '업로드',
    workflowStepTranspose: '전조',
    workflowStepDownload: '다운로드',
    workflowCaption: '',

    // Guide
    guide: '사용법',
    skip: '건너뛰기',
    next: '다음',
    done: '완료',
    dontShowAgain: '다시 보지 않기',
    guideStepOf: (n: number, total: number) => `${n} / ${total}`,
    playGuideVideo: '영상 재생',
    guideSteps: [
      {
        title: '악보 올리기',
        desc: '코드 악보 사진을 올리면 키를 자동으로 찾아요.',
        videoMobile: '휴대폰에서 악보 업로드를 누르고 사진을 고르면, 결과 화면으로 넘어가 악보를 읽은 뒤 감지된 키 D가 표시되는 영상',
        videoDesktop: '마우스로 악보 업로드를 클릭하고 사진을 고르면, 악보를 읽은 뒤 감지된 키 D가 표시되는 영상',
      },
      {
        title: '카포 고르기',
        desc: '프렛을 누르거나 +/−로 카포를 옮기면 코드가 바로 바뀌어요.',
        videoMobile: '지판의 2프렛을 눌러 카포를 끼우면 악보의 코드가 바뀌고, + 버튼으로 카포를 3프렛으로 옮기는 영상',
        videoDesktop: '마우스로 지판의 2프렛을 클릭하면 코드가 바뀐 악보가 나오고, 반음 버튼으로 카포를 3프렛으로 옮기는 영상',
      },
      {
        title: '교체 / 위에',
        desc: '원래 코드를 덮어쓰거나, 위에 따로 적어 비교할 수 있어요.',
        videoMobile: '위에를 눌러 원래 코드 위에 새 코드를 함께 보고, 교체로 돌아온 뒤 원본 보기로 원래 악보를 잠깐 보는 영상',
        videoDesktop: '마우스로 위에를 클릭해 원래 코드 위에 새 코드를 함께 보고, 교체로 돌아온 뒤 원본 보기로 원래 악보를 잠깐 보는 영상',
      },
      {
        title: '코드 고치기',
        desc: '잘못 읽힌 코드는 눌러서 고치거나 지울 수 있어요.',
        videoMobile: '감지된 코드 목록에서 코드 하나를 지우고, 위치 지정 추가로 악보 위 한 곳에 새 코드를 넣는 영상',
        videoDesktop: '마우스로 감지된 코드 하나를 지우고, 위치 지정 추가로 악보 위 한 곳에 새 코드를 넣는 영상',
      },
      {
        title: 'PNG 저장',
        desc: "바뀐 악보를 이미지로 저장해요. 아이폰은 공유 메뉴에서 '이미지 저장'을 고르세요.",
        videoMobile: 'PNG 다운로드를 눌러 바뀐 악보를 이미지로 저장하는 영상',
        videoDesktop: '마우스로 PNG 다운로드를 클릭해 바뀐 악보 이미지가 내려받아지는 영상',
      },
    ],

    // Footer
    footerTagline: '코드 악보 변환기 & 카포 도구',
    privacy: '개인정보 처리 안내',
    terms: '이용약관',

    // History
    historyTitle: '내 작업',
    totalJobs: '전체 작업',
    completed: '완료',
    failed: '실패',
    loading: '로딩 중…',
    retry: '다시 시도',
    noJobs: '처리된 악보가 없습니다.',
    processFirst: '첫 번째 악보 처리하기',
    download: '다운로드',
    delete: '삭제',
    semitones: (n: number) => `${n > 0 ? '+' : ''}${n} 반음`,
    deleteConfirm: (name: string) => `"${name}" 작업을 삭제하시겠습니까?`,
    downloadFailed: (msg: string) => `다운로드 실패: ${msg}`,
    deleteFailed: (msg: string) => `삭제 실패: ${msg}`,
    untitled: '제목 없음',
    loadingDots: '로딩 중…',

    // Mobile (≤640px) home and result board
    mUploadLimits: 'JPG · PNG · 최대 20 MB',
    mReadingSheet: '악보를 읽고 있어요…',
    mDetectedKey: '감지된 키',
    mPickCapo: '카포를 골라 주세요',
    mCapoN: (n: number) => `카포 ${n}`,
    mShiftSemitones: (n: number) => `반음 ${n > 0 ? '+' : '−'}${Math.abs(n)}`,
    mSemitoneValue: (n: number) => `${n > 0 ? '+' : '−'}${Math.abs(n)} 반음`,
    mOutOfRangeDown: '카포 범위 밖 · 키 내리기',
    mKeyUpNoCapo: '카포 없이 키 올리기',
    mCapoUp: '카포 한 프렛 올리기',
    mCapoDown: '카포 한 프렛 내리기',
    mKeyDownStep: '카포 없이 키 반음 내리기',
    mKeyUpStep: '카포 없이 키 반음 올리기',
    mDisplayMode: '표시 방식',
    mBack: '뒤로',
    mUploadAnother: '다른 악보 올리기',
    mOpenMenu: '메뉴 열기',

  },

  en: {
    // Nav
    myJobs: 'My Jobs',
    login: 'Login',
    logout: 'Logout',

    // Hero
    subtitle: 'Choose a key shift',
    heroHeadline: 'Transpose chord sheets easily',
    heroSubcopy: '',
    heroTrust: 'PNG · JPG · no signup',
    heroPrimaryCta: 'Upload sheet',

    // Upload
    uploadSheet: 'Upload Sheet',
    changeSheet: 'Change Sheet',
    detectingChords: 'Detecting chords…',
    detectedKey: 'Detected key:',
    uploadFirst: 'Upload a sheet first',
    onlyPngJpg: 'Only PNG and JPG files are supported.',
    fileTooLarge: 'File size exceeds the 20MB limit.',
    uploadTooLarge: 'The image is too large or has too many pixels. Use an image under 20MB and 50 megapixels.',
    invalidUpload: 'This image could not be processed. Choose a valid, static PNG or JPEG image.',
    ocrBusy: 'Chord detection is busy. Please try again shortly.',
    detectionExpired: 'The previous detection has expired. Upload the sheet again.',
    failedConnect: 'Failed to connect to server.',
    closeMenu: 'Close menu',
    transposeDown: 'Transpose down one semitone',
    transposeUp: 'Transpose up one semitone',
    capoSelector: 'Capo fret selector',
    selectCapoFret: (n: number) => `Select capo fret ${n}`,

    // Fretboard
    capo: 'Capo',
    none: 'None',
    fret: 'Fret',
    open: 'Open',
    capoPosition: 'Capo Position',
    transposeUpInfo: (n: number) => `+${n} semitones`,

    // Options
    rendering: 'Rendering…',
    updating: 'Updating…',

    // Result
    replace: 'Replace',
    above: 'Above',
    viewOriginal: 'View Original',
    viewRendered: 'View Rendered',
    downloadPng: 'Download PNG',
    longPressToSave: 'Press and hold the image to save it',
    saveImageTitle: 'Transposed chord sheet image',
    closeDialog: 'Close',
    originalSheetAlt: 'Original uploaded chord sheet',
    renderedSheetAlt: (mode: string) => `Transposed chord sheet in ${mode} mode`,

    // Empty state
    uploadYourScore: 'Upload Your Music Score',
    uploadCta: 'Upload Chord Sheet',
    uploadHint: 'PNG · JPG supported · max 20MB',
    workflowStepUpload: 'Upload',
    workflowStepTranspose: 'Transpose',
    workflowStepDownload: 'Download',
    workflowCaption: '',

    // Guide
    guide: 'How to Use',
    skip: 'Skip',
    next: 'Next',
    done: 'Done',
    dontShowAgain: "Don't show again",
    guideStepOf: (n: number, total: number) => `${n} / ${total}`,
    playGuideVideo: 'Play video',
    guideSteps: [
      {
        title: 'Upload a sheet',
        desc: 'Upload a photo of a chord sheet and the key is found automatically.',
        videoMobile: 'On a phone, tapping Upload sheet and choosing a photo opens the result screen, which reads the sheet and shows the detected key D',
        videoDesktop: 'Clicking Upload sheet and choosing a photo reads the sheet and shows the detected key D',
      },
      {
        title: 'Pick a capo',
        desc: 'Tap a fret or use + / − to move the capo, and the chords change right away.',
        videoMobile: 'Tapping fret 2 puts the capo on and the chords on the sheet change; the + button then moves the capo to fret 3',
        videoDesktop: 'Clicking fret 2 shows the sheet with changed chords; the semitone button then moves the capo to fret 3',
      },
      {
        title: 'Replace / Above',
        desc: 'Overwrite the original chords, or write the new ones above them to compare.',
        videoMobile: 'Tapping Above shows the new chords over the original ones, Replace switches back, and View original briefly shows the original sheet',
        videoDesktop: 'Clicking Above shows the new chords over the original ones, Replace switches back, and View original briefly shows the original sheet',
      },
      {
        title: 'Fix a chord',
        desc: 'Tap a misread chord to fix it, or remove it.',
        videoMobile: 'One chord is removed from the detected list, and Add at position places a new chord on the sheet',
        videoDesktop: 'One detected chord is removed with the mouse, and Add at position places a new chord on the sheet',
      },
      {
        title: 'Save as PNG',
        desc: "Save the transposed sheet as an image. On iPhone, choose 'Save Image' in the share menu.",
        videoMobile: 'Tapping Download PNG saves the transposed sheet as an image',
        videoDesktop: 'Clicking Download PNG downloads the transposed sheet as an image',
      },
    ],

    // Footer
    footerTagline: 'Chord Sheet Transposer & Capo Tool',
    privacy: 'Privacy',
    terms: 'Terms',

    // History
    historyTitle: 'My Jobs',
    totalJobs: 'Total Jobs',
    completed: 'Completed',
    failed: 'Failed',
    loading: 'Loading…',
    retry: 'Retry',
    noJobs: 'No processed sheets yet.',
    processFirst: 'Process Your First Sheet',
    download: 'Download',
    delete: 'Delete',
    semitones: (n: number) => `${n > 0 ? '+' : ''}${n} semitones`,
    deleteConfirm: (name: string) => `Delete "${name}" job?`,
    downloadFailed: (msg: string) => `Download failed: ${msg}`,
    deleteFailed: (msg: string) => `Delete failed: ${msg}`,
    untitled: 'Untitled',
    loadingDots: 'Loading…',

    // Mobile (≤640px) home and result board
    mUploadLimits: 'JPG · PNG · up to 20 MB',
    mReadingSheet: 'Reading your sheet…',
    mDetectedKey: 'Detected key',
    mPickCapo: 'Choose a capo',
    mCapoN: (n: number) => `Capo ${n}`,
    mShiftSemitones: (n: number) => `${n > 0 ? '+' : '−'}${Math.abs(n)} ${Math.abs(n) === 1 ? 'semitone' : 'semitones'}`,
    mSemitoneValue: (n: number) => `${n > 0 ? '+' : '−'}${Math.abs(n)} ${Math.abs(n) === 1 ? 'semitone' : 'semitones'}`,
    mOutOfRangeDown: 'Beyond capo range · key down',
    mKeyUpNoCapo: 'Key up, no capo',
    mCapoUp: 'Move capo up one fret',
    mCapoDown: 'Move capo down one fret',
    mKeyDownStep: 'Lower the key one semitone without a capo',
    mKeyUpStep: 'Raise the key one semitone without a capo',
    mDisplayMode: 'Display mode',
    mBack: 'Back',
    mUploadAnother: 'Upload another sheet',
    mOpenMenu: 'Open menu',

  },
};

export type T = typeof translations['en'];
