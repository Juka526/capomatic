import LegalPage from '@/components/LegalPage';

const sections = {
  ko: [
    { heading: '서비스', paragraphs: [
      'Capomatic은 PNG·JPEG 코드 악보에서 코드를 감지하고 전조·카포 조정 결과 이미지를 만드는 도구입니다. 로그인과 브라우저별 작업 기록을 제공하지만, V1에는 관리자 기능이나 유료 GPT 보정이 포함되지 않습니다.',
    ] },
    { heading: '정확도와 사용 책임', paragraphs: [
      'OCR과 자동 전조 결과에는 누락이나 오인식이 있을 수 있습니다. 공연, 예배 또는 배포 전에 사용자가 코드와 결과 악보를 직접 확인해야 합니다. 서비스는 음악적·법률적 판단을 대신하지 않습니다.',
    ] },
    { heading: '저작권과 업로드할 수 있는 악보', paragraphs: [
      '악보(가사, 멜로디, 코드 진행, 편곡, 악보 디자인 포함)의 저작권은 작사·작곡·편곡자, 음악 출판사 등 원래 권리자에게 있습니다. Capomatic은 악보에 대한 어떠한 권리도 갖거나 주장하지 않으며, 사용자에게 권리를 부여하지도 않습니다.',
      '다음 중 하나에 해당하는 악보만 업로드해 주세요.',
      '· 직접 만든 악보',
      '· 정당하게 구입했거나 이용 허락을 받은 악보',
      '· 소속 교회·단체가 이용 허락(예: 교회 저작권 라이선스)을 받아 사용하는 악보',
      '· 저작권 보호 기간이 끝났거나 자유 이용이 허락된 악보',
      '불법으로 복제·유통된 악보, 타인의 개인정보가 담긴 자료는 업로드할 수 없습니다.',
      '업로드한 자료에 필요한 권리를 확보할 책임은 사용자에게 있습니다.',
    ] },
    { heading: '결과물의 이용 범위', paragraphs: [
      'Capomatic이 만든 결과 이미지는 원래 악보에 전조된 코드를 덧붙인 것으로, 원래 악보의 저작권은 그대로 원래 권리자에게 있습니다.',
      '결과 이미지는 본인 또는 함께 연주하는 팀의 연습·연주를 위한 개인적인 용도로만 사용해 주세요.',
      '권리자의 허락 없이 결과 이미지를 다음과 같이 이용해서는 안 됩니다.',
      '· 웹사이트, 블로그, SNS, 공개 카페·커뮤니티 등에 게시',
      '· 판매하거나 유료로 제공',
      '· 불특정 다수에게 배포',
      '· 악보집이나 다른 서비스의 자료로 사용',
      '교회나 단체에서 결과물을 복사·배포·화면 송출하는 경우, 해당 교회·단체가 가진 이용 허락의 범위 안에서만 사용해 주세요.',
    ] },
    { heading: '서비스가 하는 일과 하지 않는 일', paragraphs: [
      'Capomatic은 사용자가 이미 가진 악보에서 코드를 읽고 조를 바꿔 보여주는 도구입니다. 악보를 판매하거나 배포하지 않으며, 악보 검색·공유 기능을 제공하지 않습니다.',
      '업로드한 악보는 결과를 만드는 데만 사용되고 다른 사용자에게 공개되지 않습니다. 영구 저장소에 보관되지 않으며 AI 학습에 사용되지 않습니다. 자세한 보관 방식은 개인정보 처리 안내를 확인해 주세요.',
      '서비스 후원은 도구 개발과 운영에 대한 것이며, 악보나 결과물의 대가가 아닙니다.',
    ] },
    { heading: '권리자 신고와 조치', paragraphs: [
      '저작권을 침해하는 이용이 확인되었다고 생각하는 권리자는 아래 문의 경로로 다음 내용을 알려 주세요.',
      '· 권리자 정보와 연락처',
      '· 대상 저작물',
      '· 침해로 보는 이유와 확인할 수 있는 정보(예: 결과 이미지가 게시된 위치)',
      '운영자는 신고를 확인한 뒤 필요한 조치를 하고, 결과를 회신합니다. 조치에는 관련 기능 제한이나 이용 제한이 포함될 수 있습니다.',
      '서비스에는 악보를 공개적으로 게시하는 기능이 없으므로, 외부에 게시된 결과물은 게시한 사람과 해당 사이트에 삭제를 요청해야 할 수 있습니다.',
    ] },
    { heading: '위반 시 이용 제한', paragraphs: [
      '저작권을 침해하는 방식으로 서비스를 반복 이용하는 경우, 운영자는 해당 계정의 이용을 제한할 수 있습니다.',
    ] },
    { heading: 'Capomatic의 권리', paragraphs: [
      'Capomatic 이름, 로고, 화면 디자인과 소스 코드에 대한 권리는 운영자에게 있습니다.',
      '위 내용은 법률 자문이 아닙니다. 이용 가능 여부가 불확실하면 권리자나 소속 단체에 확인해 주세요.',
    ] },
    { heading: '가용성과 변경', paragraphs: [
      '서비스는 예고 없이 일시 중단되거나 변경될 수 있습니다. 악보와 결과물의 유일한 보관 장소로 사용하지 말고 필요한 파일은 직접 저장해야 합니다.',
    ] },
  ],
  en: [
    { heading: 'The service', paragraphs: [
      'Capomatic detects chords in PNG or JPEG chord sheets and creates transposed or capo-adjusted result images. It provides login and browser-specific job history. Administrator features and paid GPT refinement are not part of V1.',
    ] },
    { heading: 'Accuracy and responsibility', paragraphs: [
      'OCR and automatic transpose results may contain omissions or recognition errors. You must check the chords and result sheet before a performance, worship service, or distribution. Capomatic does not replace musical or legal judgment.',
    ] },
    { heading: 'Copyright and what you may upload', paragraphs: [
      'Copyright in sheet music (including lyrics, melody, chord progression, arrangement and engraving) belongs to the original rights holders, such as the songwriters, arrangers and music publishers. Capomatic does not own or claim any rights in your sheet music and does not grant you any.',
      'Only upload sheet music that meets one of these conditions:',
      '· you created it yourself;',
      '· you purchased it or were licensed to use it;',
      '· your church or organisation is licensed to use it (for example, under a church copyright licence);',
      '· it is in the public domain or freely licensed.',
      'Do not upload illegally copied or distributed sheet music, or material that contains other people’s personal information.',
      'You are responsible for securing any rights the material you upload requires.',
    ] },
    { heading: 'How you may use the results', paragraphs: [
      'A result image is your original sheet with transposed chords added. Copyright in the original sheet stays with its rights holders.',
      'Use result images only for personal practice and performance, by you or the group you play with.',
      'Without the rights holder’s permission, you may not:',
      '· post them on websites, blogs, social media or public communities;',
      '· sell them or offer them for a fee;',
      '· distribute them to the general public;',
      '· use them in songbooks or as material for another service.',
      'If your church or organisation copies, distributes or projects the results, stay within the scope of its licence.',
    ] },
    { heading: 'What the service does and does not do', paragraphs: [
      'Capomatic is a tool that reads chords from sheet music you already have and shows them in a different key. It does not sell or distribute sheet music, and it has no sheet music search or sharing features.',
      'Uploaded sheets are used only to produce your result and are not shown to other users. They are not kept in permanent storage and are not used for AI training. See the Privacy notice for details on retention.',
      'Support payments go towards developing and running the tool. They are not payment for sheet music or results.',
    ] },
    { heading: 'Reports from rights holders', paragraphs: [
      'If you are a rights holder and believe the service is being used to infringe your copyright, contact us through the channel below with:',
      '· who you are and how to reach you;',
      '· the work concerned;',
      '· why you believe it is infringing, with information we can check (for example, where a result image was posted).',
      'We will review the report, take appropriate action and reply. Action may include restricting the related feature or a user’s access.',
      'The service has no feature for publicly posting sheets, so for results posted elsewhere you may also need to ask the person who posted them, and the site hosting them, to remove them.',
    ] },
    { heading: 'Restricting access after violations', paragraphs: [
      'We may restrict access for accounts that repeatedly use the service in ways that infringe copyright.',
    ] },
    { heading: 'Capomatic’s own rights', paragraphs: [
      'Rights in the Capomatic name, logo, interface design and source code belong to the operator.',
      'This section is not legal advice. If you are unsure whether you may use a piece of music, check with the rights holder or your organisation.',
    ] },
    { heading: 'Availability and changes', paragraphs: [
      'The service may be interrupted or changed without notice. Do not use it as the only storage location for a sheet or result; save files you need.',
    ] },
  ],
};

export default function TermsPage() {
  return <LegalPage title={{ ko: '이용약관', en: 'Terms of Use' }} sections={sections} updated="2026-10-13" />;
}
