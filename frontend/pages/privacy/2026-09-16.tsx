import LegalPage, { type Section } from '@/components/LegalPage';

// The policy in force until 2026-10-13, kept reachable as the guideline asks.
const sections: { ko: Section[]; en: Section[] } = {
  ko: [
    { heading: '이전 버전 안내', paragraphs: [
      '이 문서는 2026-10-13 이전에 적용되던 내용입니다.',
      { href: '/privacy', text: '현재 개인정보 처리방침 보기' },
    ] },
    { heading: '처리하는 정보', paragraphs: [
      '코드 악보 이미지와 변환 설정은 악보를 분석하고 결과 이미지를 만들기 위해 처리됩니다. 로그인하면 Auth0가 이름, 이메일 주소, 프로필 이미지와 같은 계정 정보를 처리합니다.',
      '내 작업 목록은 현재 계정 서버가 아니라 사용 중인 브라우저의 localStorage에 저장됩니다. 최근 작업 최대 50개에는 곡 제목, 원래 조, 목표 조, 반음 이동량, 시각이 저장되지만 악보 이미지나 서버 감지 ID는 저장되지 않습니다. Vercel Analytics가 페이지 이용에 관한 기술적 정보를 수집할 수 있고, Sentry가 오류 및 제한적으로 표본 추출된 성능 정보를 처리할 수 있습니다. 오류 추적은 기본 개인정보 전송을 끈 상태로 설정됩니다.',
    ] },
    { heading: '이미지 보관 방식', paragraphs: [
      '업로드 이미지는 OCR 처리 중 임시 파일로 사용된 뒤 삭제됩니다. 최근 감지 결과와 이미지는 후속 렌더링을 위해 서버 메모리의 최대 20개 항목·총 8천만 픽셀 캐시에 일시 보관되며, 교체되거나 서버가 재시작되면 사라집니다. 영구 이미지 저장소에는 저장하지 않습니다. 감지 ID가 사라지면 악보를 다시 업로드해야 합니다.',
    ] },
    { heading: '제3자 처리', paragraphs: [
      '서비스는 화면 제공에 Vercel, OCR 처리에 Hugging Face 인프라, 로그인에 Auth0, 오류 추적에 Sentry를 사용합니다. V1에서는 유료 GPT 보정을 제공하지 않으며 업로드 이미지를 OpenAI로 보내지 않습니다.',
    ] },
    { heading: '사용자의 선택', paragraphs: [
      '내 작업 기록은 브라우저에서 개별 삭제하거나 사이트 데이터를 지워 제거할 수 있습니다. 로그아웃으로 Auth0 세션을 종료할 수 있습니다. 계정 정보 관련 요청과 정책 문의는 프로젝트 GitHub 저장소의 Issues를 통해 운영자에게 보낼 수 있습니다.',
    ] },
  ],
  en: [
    { heading: 'Previous version', paragraphs: [
      'This version applied until 2026-10-13.',
      { href: '/privacy', text: 'See the current Privacy Policy' },
    ] },
    { heading: 'Information we process', paragraphs: [
      'Chord-sheet images and transpose settings are processed to detect chords and produce result images. If you sign in, Auth0 processes account details such as your name, email address, and profile image.',
      'Your job list is stored in your browser localStorage, not in an account database. Up to 50 recent entries contain song title, original key, target key, semitone shift, and time, but no sheet image or server detection ID. Vercel Analytics may collect technical page-usage information, and Sentry may process errors and a limited sample of performance data. Error tracking is configured not to send default personal information.',
    ] },
    { heading: 'Image retention', paragraphs: [
      'Uploaded images are used as temporary files during OCR and then deleted. The latest detections and images are held temporarily in an in-memory cache of at most 20 entries and 80 million total image pixels for follow-up rendering. They disappear on eviction or server restart and are not saved in permanent image storage. If a detection ID is lost, you must upload the sheet again.',
    ] },
    { heading: 'Service providers', paragraphs: [
      'Capomatic uses Vercel to serve the site, Hugging Face infrastructure for OCR, Auth0 for login, and Sentry for error tracking. Paid GPT refinement is unavailable in V1, and uploaded images are not sent to OpenAI.',
    ] },
    { heading: 'Your choices', paragraphs: [
      'You can delete individual job-history entries or clear site data in your browser. Logging out ends the Auth0 session. Send account-data requests or policy questions to the operator through Issues in the project GitHub repository.',
    ] },
  ],
};

export default function PreviousPrivacyPage() {
  return <LegalPage title={{ ko: '개인정보 처리방침 (2026-09-16, 이전 버전)', en: 'Privacy Policy (2026-09-16, previous version)' }} sections={sections} updated="2026-09-16" />;
}
