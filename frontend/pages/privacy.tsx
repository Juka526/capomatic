import LegalPage, { type Block, type Section } from '@/components/LegalPage';
import { PRIVACY_CONTACT_EMAIL, PRIVACY_OFFICER_NAME } from '@/lib/legal-contact';
import { supportUrl } from '@/lib/support-link.mjs';

// The Toss build has no login, job history, Vercel Analytics or support link,
// so its policy must not mention them (and the web policy names no Toss-only processing).
const IS_TOSS = process.env.NEXT_PUBLIC_APP_TARGET === 'toss';
// Short-circuit on IS_TOSS so the minifier drops the support sentences from the Toss bundle.
const HAS_SUPPORT = !IS_TOSS && Boolean(supportUrl(process.env.NEXT_PUBLIC_SUPPORT_URL, process.env.NEXT_PUBLIC_APP_TARGET));

function officer(nameLabel: string, emailLabel: string): Block[] {
  const rows = [
    PRIVACY_OFFICER_NAME && `${nameLabel}: ${PRIVACY_OFFICER_NAME}`,
    PRIVACY_CONTACT_EMAIL && `${emailLabel}: ${PRIVACY_CONTACT_EMAIL}`,
  ].filter((row): row is string => Boolean(row));
  return rows.length ? [{ list: rows }] : [];
}

const ko: Section[] = [
  { heading: '서문', paragraphs: [
    'Capomatic(이하 ‘서비스’) 운영자는 「개인정보 보호법」에 따라 정보주체의 개인정보를 보호하고 이와 관련한 고충을 신속하고 원활하게 처리할 수 있도록 다음과 같이 개인정보 처리방침을 수립·공개합니다.',
    IS_TOSS
      ? '이 처리방침은 토스 앱 안에서 제공되는 Capomatic 미니앱에 적용됩니다.'
      : '이 처리방침은 Capomatic 웹사이트에 적용됩니다.',
  ] },
  { heading: '1. 개인정보의 처리 목적', paragraphs: [
    '서비스는 다음 목적을 위해 개인정보를 처리하며, 목적이 바뀌면 법령에 따라 필요한 조치를 합니다.',
    { list: [
      '악보 분석과 결과 이미지 생성',
      ...(IS_TOSS ? [] : ['회원가입·로그인과 계정 식별']),
      '오류 추적과 서비스 안정성 확보',
      ...(IS_TOSS ? [] : ['서비스 이용 통계']),
      '문의 처리',
    ] },
    '이 처리는 정보주체와의 계약(서비스 이용)을 이행하기 위한 것으로, 「개인정보 보호법」 제15조제1항제4호에 근거하며 별도의 동의를 받지 않습니다.',
  ] },
  { heading: '2. 처리하는 개인정보의 항목', paragraphs: [
    { table: [
      ['구분', '항목', '필수·선택', '수집 방법'],
      ['악보 분석', '악보 이미지, 변환 설정(반음 이동, 표시 방식, 직접 고친 코드)', '필수(기능 이용 시)', '사용자가 업로드·입력'],
      ...(IS_TOSS ? [] : [['로그인', '이메일 주소, 비밀번호(Auth0가 암호화해 보관하며 운영자는 볼 수 없음), Auth0가 만드는 이름·닉네임·프로필 이미지 주소', '선택', '회원가입·로그인 시 입력']]),
      ['자동 생성', IS_TOSS
        ? 'IP 주소, 브라우저·기기 정보, 접속 일시, 오류 정보'
        : 'IP 주소, 브라우저·기기 정보, 접속 일시, 방문한 페이지(이용 통계), 오류 정보', '자동', '서비스 이용 시 자동 생성'],
      ['기기에만 저장', IS_TOSS
        ? '언어 설정, 사용법 안내를 닫았는지 여부'
        : '작업 기록(곡 제목, 원래 조, 목표 조, 반음 이동량, 시각, 최대 50개), 언어 설정, 사용법 안내를 닫았는지 여부, 로그인 정보(Auth0 토큰과 프로필)', '자동', '기기의 브라우저 저장소(localStorage)에 저장, 운영자 서버로 보내지 않음'],
      ['문의', '이메일 주소, 문의 내용', '필수(문의 시)', '이메일'],
    ] },
    ...(IS_TOSS ? [] : ['작업 기록에는 악보 이미지나 서버의 감지 ID가 저장되지 않습니다.']),
  ] },
  { heading: '3. 14세 미만 아동의 개인정보 처리', paragraphs: [
    '서비스는 14세 미만 아동을 대상으로 하지 않으며, 14세 미만 아동의 개인정보를 알면서 수집하지 않습니다. 법정대리인은 ‘개인정보 보호책임자’ 항목의 연락처로 아동의 개인정보 삭제를 요청할 수 있습니다.',
  ] },
  { heading: '4. 개인정보의 처리 및 보유 기간', paragraphs: [
    { table: [
      ['항목', '보유 기간'],
      ['업로드한 악보 이미지(임시 파일)', 'OCR 처리 직후 삭제'],
      ['악보 이미지와 감지 결과(서버 메모리)', '최대 20개·총 8천만 픽셀까지 보관하며, 새 작업에 밀려나거나 서버가 다시 시작되면 삭제'],
      ...(IS_TOSS ? [] : [['계정 정보(Auth0)', '계정 삭제를 요청할 때까지']]),
      ['오류 정보(Sentry)', '최대 90일(Sentry 요금제의 보존 기간)'],
      ...(IS_TOSS ? [] : [['이용 통계(Vercel Analytics)', '방문자 구분 값은 24시간 안에 폐기하며, 개인을 식별하지 않는 집계 통계는 Vercel 요금제의 보고 기간(1~24개월) 동안 보관']]),
      ['접속 기록(서버 제공 업체)', '각 수탁자의 보존 정책에 따름'],
      ['기기에 저장된 정보', '사용자가 지울 때까지'],
      ['문의 이메일', '처리 완료 후 지체 없이 파기'],
    ] },
  ] },
  { heading: '5. 개인정보의 파기 절차 및 방법', paragraphs: [
    '보유 기간이 끝나거나 처리 목적을 달성한 개인정보는 지체 없이 파기합니다.',
    { list: [
      '업로드 이미지의 임시 파일은 처리가 끝나면 서버에서 삭제합니다.',
      '서버 메모리의 이미지는 캐시에서 밀려나거나 서버가 다시 시작되면 사라집니다.',
      ...(IS_TOSS ? [] : ['계정 삭제를 요청하면 운영자가 Auth0에서 계정을 삭제합니다.']),
      '문의 이메일은 처리가 끝나면 삭제합니다.',
      '전자적 파일은 삭제하며, 종이 문서로는 개인정보를 처리하지 않습니다.',
    ] },
  ] },
  { heading: '6. 개인정보의 제3자 제공', paragraphs: [
    '운영자는 정보주체의 개인정보를 제3자에게 제공하지 않습니다. 다만 법령에 특별한 규정이 있는 경우는 예외입니다.',
  ] },
  { heading: '7. 추가적인 이용·제공의 판단 기준', paragraphs: [
    '운영자는 「개인정보 보호법」 제15조제3항 및 제17조제4항에 따른 추가적인 이용·제공을 하지 않습니다.',
  ] },
  { heading: '8. 개인정보 처리업무의 위탁', paragraphs: [
    '운영자는 서비스 제공을 위해 다음과 같이 개인정보 처리업무를 위탁하고 있습니다.',
    { table: [
      ['수탁자', '위탁 업무'],
      ...(IS_TOSS ? [] : [['Vercel Inc.', '웹사이트 제공(호스팅), 이용 통계(Vercel Analytics)']]),
      ['Hugging Face SAS', '악보 분석(OCR)과 결과 이미지 생성 서버 운영'],
      ...(IS_TOSS ? [] : [['Okta, Inc. (Auth0)', '회원가입·로그인']]),
      ['Functional Software, Inc. (Sentry)', '오류 추적'],
    ] },
    ...(IS_TOSS ? ['미니앱 화면 파일은 앱인토스 플랫폼을 통해 제공되며, 토스 앱 이용에 관한 개인정보 처리는 토스의 개인정보 처리방침을 따릅니다.'] : []),
    ...(HAS_SUPPORT ? ['후원 링크를 누르면 카카오페이 화면으로 이동하며, 이후의 처리는 카카오페이의 방침을 따릅니다. 데스크톱의 후원 QR 코드는 브라우저에서 직접 만들어지며 외부 서비스로 전송되지 않습니다.'] : []),
  ] },
  { heading: '9. 개인정보의 국외 이전', paragraphs: [
    '운영자는 서비스 제공을 위해 다음과 같이 개인정보를 국외에 처리위탁·보관합니다. 법적 근거는 「개인정보 보호법」 제28조의8제1항제3호(정보주체와의 계약 이행을 위한 국외 처리위탁·보관으로서 이 처리방침에 공개한 경우)입니다.',
    { table: [
      ['이전받는 자(연락처)', '국가', '이전 항목', '시기와 방법', '목적', '보유·이용 기간', '거부 방법과 효과'],
      ...(IS_TOSS ? [] : [['Vercel Inc. (privacy@vercel.com)', '미국(가까운 Vercel 엣지 서버를 거칠 수 있음)', 'IP 주소, 브라우저·기기 정보, 접속 기록, 이용 통계', '서비스 이용 시 네트워크를 통해 전송', '웹사이트 제공, 이용 통계', '4번 항목과 같음', '웹사이트를 이용하지 않으면 됩니다. 이 경우 서비스를 이용할 수 없습니다.']]),
      ['Hugging Face SAS (privacy@huggingface.co)', '미국', '악보 이미지, 변환 설정, IP 주소', '악보를 올릴 때 네트워크를 통해 전송', '악보 분석, 결과 이미지 생성', '4번 항목과 같음', '악보를 올리지 않으면 됩니다. 이 경우 악보 분석과 전조를 이용할 수 없습니다.'],
      ...(IS_TOSS ? [] : [['Okta, Inc. (privacy@okta.com)', '미국', '이메일 주소, 비밀번호, 이름·닉네임, 프로필 이미지, 로그인 기록', '회원가입·로그인 시 네트워크를 통해 전송', '회원가입·로그인', '계정 삭제를 요청할 때까지', '로그인하지 않으면 됩니다. 로그인하지 않아도 악보 분석을 이용할 수 있습니다.']]),
      ['Functional Software, Inc. (compliance@sentry.io)', '미국, 독일', '오류 정보, 브라우저·기기 정보', '오류가 생길 때 네트워크를 통해 전송', '오류 추적, 서비스 안정성', '최대 90일', '서비스를 이용하지 않으면 됩니다. 이 경우 서비스를 이용할 수 없습니다.'],
    ] },
  ] },
  { heading: '10. 개인정보의 안전성 확보 조치', paragraphs: [
    { list: [
      '모든 통신을 HTTPS로 암호화합니다.',
      '업로드한 악보 이미지는 영구 저장소에 저장하지 않고 처리 후 삭제합니다.',
      '업로드 파일의 형식(PNG·JPEG)과 크기(20MB)를 검사합니다.',
      '접근 키 등 비밀 값은 소스 코드가 아닌 환경 변수로 관리합니다.',
      '오류 보고에서 기본 개인정보, 요청 본문, 지역 변수를 보내지 않도록 설정합니다.',
      ...(IS_TOSS ? [] : ['계정 비밀번호는 Auth0가 암호화해 보관하며 운영자는 볼 수 없습니다.']),
    ] },
  ] },
  { heading: '11. 민감정보와 가명정보', paragraphs: [
    '서비스는 민감정보와 가명정보를 처리하지 않습니다.',
  ] },
  { heading: '12. 개인정보 자동 수집 장치의 설치·운영 및 거부', paragraphs: IS_TOSS ? [
    '토스 미니앱은 쿠키를 사용하지 않습니다. 언어 설정과 사용법 안내를 닫았는지 여부를 기기의 저장소(localStorage)에 저장하며, 이 정보는 운영자 서버로 보내지 않습니다.',
    '토스 앱에서 미니앱 데이터를 삭제하면 저장된 설정이 지워집니다. 설정이 지워져도 서비스는 이용할 수 있습니다.',
  ] : [
    '쿠키는 웹사이트가 브라우저에 보내 저장하는 작은 정보로, 다음에 접속할 때 브라우저가 웹사이트로 자동으로 다시 보냅니다. 서비스는 로그인을 위해서만 쿠키를 사용합니다.',
    { table: [
      ['이름', '목적', '보관 기간'],
      ['auth0.(클라이언트 ID).is.authenticated, _legacy_auth0.(클라이언트 ID).is.authenticated', '로그인 상태 확인(로그인한 경우에만 설정)', '1일'],
      ['Auth0 로그인 화면(*.auth0.com)의 세션 쿠키', '로그인 처리', 'Auth0 설정에 따름'],
    ] },
    'Vercel Analytics는 쿠키를 사용하지 않습니다.',
    '서비스는 다음 정보를 기기의 브라우저 저장소(localStorage)에 저장하며, 이 정보는 운영자 서버로 보내지 않습니다.',
    { table: [
      ['이름', '내용', '목적'],
      ['tc-history', '작업 기록 최대 50개', '내 작업 화면'],
      ['tc-lang', '언어 설정', '언어 유지'],
      ['tc-guide-dismissed', '사용법 안내를 닫았는지 여부', '안내 반복 방지'],
      ['@@auth0spajs@@로 시작하는 항목', '로그인 토큰과 프로필', '로그인 유지'],
    ] },
    '쿠키나 저장소를 거부하려면 다음 방법을 이용할 수 있습니다. 쿠키를 거부하면 로그인이 동작하지 않고, 저장소를 막거나 지우면 작업 기록과 언어 설정이 유지되지 않습니다. 악보 분석은 계속 이용할 수 있습니다.',
    { list: [
      '크롬(Chrome): 오른쪽 위 ‘⁝’ 선택 > 새 시크릿 창(Ctrl+Shift+N)',
      '엣지(Edge): 오른쪽 위 ‘···’ 선택 > 새 InPrivate 창(Ctrl+Shift+N)',
      '사파리(Safari, Mac): Safari > 설정 > 개인정보 보호 > 모든 쿠키 차단',
      '모바일 크롬: 오른쪽 위 ‘⁝’ 선택 > 새 시크릿 탭',
      '모바일 사파리: 설정 > 앱 > Safari > 고급 > 모든 쿠키 차단',
    ] },
    '이미 저장된 정보는 브라우저 설정에서 이 사이트의 데이터를 삭제해 지울 수 있습니다.',
  ] },
  { heading: '13. 행태정보의 수집·이용과 맞춤형 광고', paragraphs: [
    IS_TOSS
      ? '서비스는 맞춤형 광고를 위한 행태정보를 수집하지 않으며, 제3자가 행태정보를 수집하도록 허용하지 않습니다.'
      : '서비스는 맞춤형 광고를 위한 행태정보를 수집하지 않으며, 제3자가 행태정보를 수집하도록 허용하지 않습니다. Vercel Analytics는 개인을 식별하지 않는 집계 통계만 만듭니다.',
  ] },
  { heading: '14. 정보주체와 법정대리인의 권리·의무 및 행사 방법', paragraphs: [
    '정보주체는 운영자에게 언제든지 개인정보 열람, 정정, 삭제, 처리정지, 동의 철회를 요구할 수 있습니다.',
    '‘개인정보 보호책임자’ 항목의 이메일로 요구할 수 있습니다. 법정대리인이나 위임을 받은 대리인도 요구할 수 있으며, 이때는 위임장을 함께 보내 주세요.',
    '운영자는 지체 없이 조치하고 법령에서 정한 기간 안에 결과를 알려드립니다. 다만 법령에서 정한 경우에는 요구가 제한될 수 있습니다.',
    IS_TOSS
      ? '토스 앱에서 미니앱 데이터를 삭제하면 기기에 저장된 설정을 직접 지울 수 있습니다.'
      : '직접 할 수 있는 방법도 있습니다. 내 작업 화면에서 기록을 하나씩 지우거나, 브라우저에서 이 사이트의 데이터를 삭제하거나, 로그아웃할 수 있습니다. 계정 삭제는 위 이메일로 요청해 주세요.',
  ] },
  { heading: '15. 자동화된 결정', paragraphs: [
    '서비스는 정보주체에게 중대한 영향을 미치는 완전히 자동화된 결정을 하지 않습니다. 악보에서 코드를 읽는 OCR은 이에 해당하지 않습니다.',
  ] },
  { heading: '16. 개인정보 보호책임자', paragraphs: [
    '운영자는 개인정보 처리에 관한 업무를 총괄하고 관련 고충을 처리하기 위해 다음과 같이 개인정보 보호책임자를 지정하고 있습니다.',
    ...officer('성명(담당)', '이메일'),
  ] },
  { heading: '17. 국내대리인', paragraphs: [
    '운영자는 「개인정보 보호법」 제31조의2에 따른 국내대리인 지정 대상이 아닙니다.',
  ] },
  { heading: '18. 권익침해 구제 방법', paragraphs: [
    '개인정보 침해에 대한 상담이나 피해 구제가 필요하면 다음 기관에 문의할 수 있습니다.',
    { list: [
      '개인정보 분쟁조정위원회: (국번없이) 1833-6972 (www.kopico.go.kr)',
      '개인정보침해 신고센터: (국번없이) 118 (privacy.kisa.or.kr)',
      '경찰청: (국번없이) 182 (ecrm.police.go.kr)',
    ] },
  ] },
  { heading: '19. 영상정보처리기기', paragraphs: [
    '서비스는 고정형·이동형 영상정보처리기기를 운영하지 않습니다.',
  ] },
  { heading: '20. 개인정보 처리방침의 변경', paragraphs: [
    '이 개인정보 처리방침은 2026년 10월 13일부터 적용됩니다. 내용이 바뀌면 바뀐 내용과 시행일을 이 페이지에 게시합니다.',
    '이전 개인정보 처리방침',
    { href: '/privacy/2026-09-16', text: '2026-09-16 시행 버전' },
  ] },
];

const en: Section[] = [
  { heading: 'Introduction', paragraphs: [
    'The operator of Capomatic (“the service”) establishes and publishes this Privacy Policy under the Korean Personal Information Protection Act to protect personal information and to handle related complaints quickly and smoothly.',
    IS_TOSS
      ? 'This policy applies to the Capomatic mini app in the Toss app.'
      : 'This policy applies to the Capomatic website.',
    'This is a translation. If the Korean and English versions differ, the Korean version prevails.',
  ] },
  { heading: '1. Why we process personal information', paragraphs: [
    'We process personal information for these purposes, and take the steps the law requires if a purpose changes:',
    { list: [
      'analysing sheets and creating result images;',
      ...(IS_TOSS ? [] : ['sign-up, login and identifying accounts;']),
      'error tracking and keeping the service stable;',
      ...(IS_TOSS ? [] : ['usage statistics;']),
      'handling enquiries.',
    ] },
    'This processing is needed to provide the service you use, under Article 15(1)4 of the Personal Information Protection Act, and does not need separate consent.',
  ] },
  { heading: '2. What we process', paragraphs: [
    { table: [
      ['Category', 'Items', 'Required or optional', 'How it is collected'],
      ['Sheet analysis', 'Sheet image, transform settings (semitone shift, display mode, chords you corrected)', 'Required (to use the feature)', 'You upload or enter it'],
      ...(IS_TOSS ? [] : [['Login', 'Email address, password (kept encrypted by Auth0; the operator cannot see it), and the name, nickname and profile image address Auth0 creates', 'Optional', 'Entered at sign-up or login']]),
      ['Generated automatically', IS_TOSS
        ? 'IP address, browser and device information, access time, error information'
        : 'IP address, browser and device information, access time, pages visited (usage statistics), error information', 'Automatic', 'Generated when you use the service'],
      ['Stored only on your device', IS_TOSS
        ? 'Language setting, whether you closed the guide'
        : 'Job history (song title, original key, target key, semitone shift, time; up to 50 entries), language setting, whether you closed the guide, login data (Auth0 tokens and profile)', 'Automatic', 'Saved in your browser storage (localStorage); not sent to the operator’s server'],
      ['Enquiries', 'Email address, message', 'Required (when you contact us)', 'Email'],
    ] },
    ...(IS_TOSS ? [] : ['Job history contains no sheet image and no server detection ID.']),
  ] },
  { heading: '3. Children under 14', paragraphs: [
    'The service is not aimed at children under 14 and does not knowingly collect their personal information. A parent or legal guardian can ask for a child’s information to be deleted through the contact in “Privacy officer”.',
  ] },
  { heading: '4. How long we keep it', paragraphs: [
    { table: [
      ['Item', 'Retention'],
      ['Uploaded sheet image (temporary file)', 'Deleted right after OCR'],
      ['Sheet images and detection results (server memory)', 'Up to 20 entries and 80 million pixels in total; removed when pushed out by new jobs or when the server restarts'],
      ...(IS_TOSS ? [] : [['Account information (Auth0)', 'Until you ask for the account to be deleted']]),
      ['Error information (Sentry)', 'Up to 90 days (the retention of the Sentry plan)'],
      ...(IS_TOSS ? [] : [['Usage statistics (Vercel Analytics)', 'The visitor value is discarded within 24 hours; aggregated statistics that do not identify anyone are kept for the Vercel plan’s reporting window (1 to 24 months)']]),
      ['Access logs (hosting providers)', 'Under each processor’s retention policy'],
      ['Information stored on your device', 'Until you delete it'],
      ['Enquiry emails', 'Destroyed without delay once handled'],
    ] },
  ] },
  { heading: '5. How we destroy it', paragraphs: [
    'We destroy personal information without delay once its retention period ends or its purpose is achieved.',
    { list: [
      'Temporary upload files are deleted from the server when processing ends.',
      'Images in server memory disappear when they are pushed out of the cache or the server restarts.',
      ...(IS_TOSS ? [] : ['If you ask for your account to be deleted, the operator deletes it in Auth0.']),
      'Enquiry emails are deleted once handled.',
      'Electronic files are deleted. We do not process personal information on paper.',
    ] },
  ] },
  { heading: '6. Sharing with third parties', paragraphs: [
    'We do not provide personal information to third parties, except where the law specifically requires it.',
  ] },
  { heading: '7. Additional use or provision', paragraphs: [
    'We do not carry out additional use or provision under Articles 15(3) and 17(4) of the Personal Information Protection Act.',
  ] },
  { heading: '8. Processors', paragraphs: [
    'We use these processors to provide the service:',
    { table: [
      ['Processor', 'Task'],
      ...(IS_TOSS ? [] : [['Vercel Inc.', 'Website hosting, usage statistics (Vercel Analytics)']]),
      ['Hugging Face SAS', 'Running the server that analyses sheets (OCR) and creates result images'],
      ...(IS_TOSS ? [] : [['Okta, Inc. (Auth0)', 'Sign-up and login']]),
      ['Functional Software, Inc. (Sentry)', 'Error tracking'],
    ] },
    ...(IS_TOSS ? ['The mini app’s files are delivered through the Apps in Toss platform. Personal information related to using the Toss app is handled under Toss’s own privacy policy.'] : []),
    ...(HAS_SUPPORT ? ['The support link takes you to KakaoPay, and what happens there follows KakaoPay’s own policy. The support QR code on desktop is generated in your browser and is not sent to any external service.'] : []),
  ] },
  { heading: '9. Transfers outside Korea', paragraphs: [
    'We entrust processing and storage of personal information to these processors outside Korea. The legal basis is Article 28-8(1)3 of the Personal Information Protection Act (overseas processing or storage needed to perform the contract with you, disclosed in this policy).',
    { table: [
      ['Recipient (contact)', 'Country', 'Items', 'When and how', 'Purpose', 'Retention', 'How to refuse, and the effect'],
      ...(IS_TOSS ? [] : [['Vercel Inc. (privacy@vercel.com)', 'United States (requests may pass through a nearby Vercel edge server)', 'IP address, browser and device information, access logs, usage statistics', 'Sent over the network when you use the service', 'Hosting the website, usage statistics', 'As in section 4', 'Do not use the website. You will then be unable to use the service.']]),
      ['Hugging Face SAS (privacy@huggingface.co)', 'United States', 'Sheet image, transform settings, IP address', 'Sent over the network when you upload a sheet', 'Analysing sheets, creating result images', 'As in section 4', 'Do not upload sheets. You will then be unable to analyse or transpose sheets.'],
      ...(IS_TOSS ? [] : [['Okta, Inc. (privacy@okta.com)', 'United States', 'Email address, password, name, nickname, profile image, login records', 'Sent over the network at sign-up or login', 'Sign-up and login', 'Until you ask for the account to be deleted', 'Do not log in. You can still analyse sheets without logging in.']]),
      ['Functional Software, Inc. (compliance@sentry.io)', 'United States, Germany', 'Error information, browser and device information', 'Sent over the network when an error occurs', 'Error tracking, service stability', 'Up to 90 days', 'Do not use the service. You will then be unable to use it.'],
    ] },
  ] },
  { heading: '10. Security measures', paragraphs: [
    { list: [
      'All traffic is encrypted with HTTPS.',
      'Uploaded sheet images are not kept in permanent storage and are deleted after processing.',
      'Uploads are checked for format (PNG or JPEG) and size (20 MB).',
      'Secrets such as access keys are kept in environment variables, not in source code.',
      'Error reporting is configured not to send default personal information, request bodies or local variables.',
      ...(IS_TOSS ? [] : ['Account passwords are kept encrypted by Auth0; the operator cannot see them.']),
    ] },
  ] },
  { heading: '11. Sensitive and pseudonymised information', paragraphs: [
    'The service does not process sensitive or pseudonymised information.',
  ] },
  { heading: '12. Cookies and similar technology', paragraphs: IS_TOSS ? [
    'The Toss mini app does not use cookies. It saves your language setting and whether you closed the guide in your device storage (localStorage). This is not sent to the operator’s server.',
    'Clearing the mini app’s data in the Toss app deletes these settings. You can still use the service afterwards.',
  ] : [
    'A cookie is a small piece of information a website asks your browser to store, which the browser sends back on later visits. The service uses cookies only for login.',
    { table: [
      ['Name', 'Purpose', 'Retention'],
      ['auth0.(client ID).is.authenticated, _legacy_auth0.(client ID).is.authenticated', 'Checking login state (set only after you log in)', '1 day'],
      ['Session cookies of the Auth0 login page (*.auth0.com)', 'Handling login', 'Under Auth0’s settings'],
    ] },
    'Vercel Analytics does not use cookies.',
    'The service stores the following in your browser storage (localStorage). It is not sent to the operator’s server.',
    { table: [
      ['Name', 'Content', 'Purpose'],
      ['tc-history', 'Up to 50 job history entries', 'My Jobs page'],
      ['tc-lang', 'Language setting', 'Keeping your language'],
      ['tc-guide-dismissed', 'Whether you closed the guide', 'Not showing the guide again'],
      ['Entries starting with @@auth0spajs@@', 'Login tokens and profile', 'Keeping you logged in'],
    ] },
    'You can refuse cookies or storage as follows. If you refuse cookies, login will not work. If you block or clear storage, job history and your language setting are not kept. You can still analyse sheets.',
    { list: [
      'Chrome: ‘⁝’ at the top right > New Incognito window (Ctrl+Shift+N)',
      'Edge: ‘···’ at the top right > New InPrivate window (Ctrl+Shift+N)',
      'Safari (Mac): Safari > Settings > Privacy > Block all cookies',
      'Chrome on mobile: ‘⁝’ at the top right > New Incognito tab',
      'Safari on mobile: Settings > Apps > Safari > Advanced > Block All Cookies',
    ] },
    'You can delete information already stored by clearing this site’s data in your browser settings.',
  ] },
  { heading: '13. Behavioural information and targeted advertising', paragraphs: [
    IS_TOSS
      ? 'The service does not collect behavioural information for targeted advertising and does not let third parties collect it.'
      : 'The service does not collect behavioural information for targeted advertising and does not let third parties collect it. Vercel Analytics produces only aggregated statistics that do not identify anyone.',
  ] },
  { heading: '14. Your rights and how to use them', paragraphs: [
    'You can ask the operator at any time to access, correct or delete your personal information, to stop processing it, or to withdraw consent.',
    'Send your request to the email in “Privacy officer”. A legal guardian or an authorised representative can also make a request, with a letter of authorisation.',
    'We will act without delay and tell you the outcome within the period set by law. Some requests may be limited where the law provides.',
    IS_TOSS
      ? 'You can delete settings stored on your device yourself by clearing the mini app’s data in the Toss app.'
      : 'You can also act yourself: delete entries one by one on the My Jobs page, clear this site’s data in your browser, or log out. To delete your account, email us at the address above.',
  ] },
  { heading: '15. Automated decisions', paragraphs: [
    'The service does not make fully automated decisions that significantly affect you. Reading chords from a sheet with OCR is not such a decision.',
  ] },
  { heading: '16. Privacy officer', paragraphs: [
    'The operator has appointed the following privacy officer to oversee the processing of personal information and handle related complaints.',
    ...officer('Name (role)', 'Email'),
  ] },
  { heading: '17. Domestic representative', paragraphs: [
    'The operator is not required to appoint a domestic representative under Article 31-2 of the Personal Information Protection Act.',
  ] },
  { heading: '18. Remedies', paragraphs: [
    'For advice or remedies for a privacy violation, you can contact:',
    { list: [
      'Personal Information Dispute Mediation Committee: 1833-6972 (www.kopico.go.kr)',
      'Personal Information Infringement Report Center: 118 (privacy.kisa.or.kr)',
      'Korean National Police Agency: 182 (ecrm.police.go.kr)',
    ] },
  ] },
  { heading: '19. Video devices', paragraphs: [
    'The service does not operate fixed or mobile video devices.',
  ] },
  { heading: '20. Changes to this policy', paragraphs: [
    'This Privacy Policy applies from 13 October 2026. If it changes, we will post the changes and their effective date on this page.',
    'Previous privacy policies',
    { href: '/privacy/2026-09-16', text: 'Version effective 2026-09-16' },
  ] },
];

export default function PrivacyPage() {
  return <LegalPage title={{ ko: 'Capomatic 개인정보 처리방침', en: 'Capomatic Privacy Policy' }} sections={{ ko, en }} updated="2026-10-13" toc />;
}
