export type Lang = 'ko' | 'en';

export const translations = {
  ko: {
    // Nav
    admin: '관리자',
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
    fileTooLarge: '파일 크기가 8MB를 초과합니다.',
    failedConnect: '서버에 연결할 수 없습니다.',

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

    // Empty state
    featureUploadLabel: '악보 업로드',
    featureUploadDesc: 'PNG 또는 JPG 코드 악보 이미지를 업로드하세요',
    featureCapoLabel: '카포 선택',
    featureCapoDesc: '프렛보드에서 원하는 프렛을 선택하세요',
    featureDownloadLabel: '다운로드',
    featureDownloadDesc: '변환된 악보를 PNG 이미지로 받으세요',
    uploadYourScore: '악보를 업로드하세요',
    uploadCta: '악보 이미지 업로드하기',
    uploadHint: 'PNG · JPG 지원 · 최대 8MB',
    workflowStepUpload: '업로드',
    workflowStepTranspose: '전조',
    workflowStepDownload: '다운로드',
    workflowCaption: '',
    gptHybridLabel: 'AI로 더욱 정확하게',
    gptHybridDesc: '',
    gptHybridButton: 'AI로 개선',
    gptHybridRefining: 'AI 개선 중…',
    gptHybridApplied: 'AI 개선 완료',
    gptHybridUnavailable: '백엔드에 AI가 설정되어 있지 않습니다.',
    gptHybridNoChange: 'AI가 확인했지만 새 변경 사항은 없습니다.',
    gptHybridChanged: (added: number, corrected: number) => `누락 ${added}개 추가 · 코드 ${corrected}개 수정`,

    // Guide
    guide: '사용법',
    skip: '건너뛰기',
    next: '다음',
    done: '완료',

    // Footer
    footerTagline: '코드 악보 변환기 & 카포 도구',

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

    // Admin
    adminDashboard: '관리자 대시보드',
    overview: '개요',
    popularSongs: '인기 곡',
    users: '사용자',
    totalUsers: '전체 사용자',
    totalJobsStat: '전체 작업',
    cachedItems: '캐시 항목',
    cacheHitRate: '캐시 적중률',
    avgTime: '평균 시간',
    top5Songs: '인기 곡 TOP 5',
    viewAll: '전체 보기',
    noSongs: '아직 처리된 곡이 없습니다',
    popularRanking: '인기 곡 순위',
    rank: '순위',
    song: '곡명',
    original: '원래 키',
    target: '변환 키',
    semitonesCol: '반음',
    requests: '요청 수',
    uniqueUsers: '사용자 수',
    lastRequested: '마지막 요청',
    allUsers: '전체 사용자',
    email: '이메일',
    name: '이름',
    role: '역할',
    created: '가입일',
    lastLogin: '마지막 로그인',
    never: '없음',
    loadingDashboard: '대시보드 로딩 중…',
    failedLoad: '데이터를 불러오지 못했습니다',
  },

  en: {
    // Nav
    admin: 'Admin',
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
    fileTooLarge: 'File size exceeds 8MB limit.',
    failedConnect: 'Failed to connect to server.',

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

    // Empty state
    featureUploadLabel: 'Upload Sheet',
    featureUploadDesc: 'Upload a PNG or JPG chord sheet image',
    featureCapoLabel: 'Select Capo',
    featureCapoDesc: 'Pick a fret on the fretboard or use the buttons',
    featureDownloadLabel: 'Download',
    featureDownloadDesc: 'Get your transposed sheet as a PNG image',
    uploadYourScore: 'Upload Your Music Score',
    uploadCta: 'Upload Chord Sheet',
    uploadHint: 'PNG · JPG supported · max 8MB',
    workflowStepUpload: 'Upload',
    workflowStepTranspose: 'Transpose',
    workflowStepDownload: 'Download',
    workflowCaption: '',
    gptHybridLabel: 'AI OCR',
    gptHybridDesc: '',
    gptHybridButton: 'Improve with AI',
    gptHybridRefining: 'Improving…',
    gptHybridApplied: 'AI improved',
    gptHybridUnavailable: 'AI is not configured on the backend.',
    gptHybridNoChange: 'AI checked the sheet; no new changes found.',
    gptHybridChanged: (added: number, corrected: number) => `Added ${added} missing · corrected ${corrected} chords`,

    // Guide
    guide: 'How to Use',
    skip: 'Skip',
    next: 'Next',
    done: 'Done',

    // Footer
    footerTagline: 'Chord Sheet Transposer & Capo Tool',

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

    // Admin
    adminDashboard: 'Admin Dashboard',
    overview: 'Overview',
    popularSongs: 'Popular Songs',
    users: 'Users',
    totalUsers: 'Total Users',
    totalJobsStat: 'Total Jobs',
    cachedItems: 'Cached Items',
    cacheHitRate: 'Cache Hit Rate',
    avgTime: 'Avg Time',
    top5Songs: 'Top 5 Popular Songs',
    viewAll: 'View All',
    noSongs: 'No songs processed yet',
    popularRanking: 'Popular Songs Ranking',
    rank: '#',
    song: 'Song',
    original: 'Original',
    target: 'Target',
    semitonesCol: 'Semitones',
    requests: 'Requests',
    uniqueUsers: 'Users',
    lastRequested: 'Last Requested',
    allUsers: 'All Users',
    email: 'Email',
    name: 'Name',
    role: 'Role',
    created: 'Created',
    lastLogin: 'Last Login',
    never: 'Never',
    loadingDashboard: 'Loading dashboard…',
    failedLoad: 'Failed to load admin data',
  },
};

export type T = typeof translations['en'];
