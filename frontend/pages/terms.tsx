import LegalPage, { type Section } from '@/components/LegalPage';
import { supportUrl } from '@/lib/support-link.mjs';

const IS_TOSS = process.env.NEXT_PUBLIC_APP_TARGET === 'toss';
// Same gate as the support link itself: null in the Toss build or when unset.
const HAS_SUPPORT = !IS_TOSS && Boolean(supportUrl(process.env.NEXT_PUBLIC_SUPPORT_URL, process.env.NEXT_PUBLIC_APP_TARGET));

const sections: { ko: Section[]; en: Section[] } = {
  ko: [
    { heading: '서비스', paragraphs: [
      'Capomatic은 PNG·JPEG 코드 악보에서 코드를 감지하고 전조·카포 조정 결과 이미지를 만드는 개인 연습용 도구입니다. 내가 가진 악보로 내가 칠 키와 카포를 맞춰 볼 수 있습니다.',
      IS_TOSS
        ? '토스 미니앱은 로그인 없이 이용할 수 있으며 작업 기록을 저장하지 않습니다.'
        : '로그인과 브라우저별 작업 기록을 제공하지만, V1에는 관리자 기능이나 유료 GPT 보정이 포함되지 않습니다.',
    ] },
    { heading: '정확도와 사용 책임', paragraphs: [
      'OCR과 자동 전조 결과에는 누락이나 오인식이 있을 수 있습니다. 결과 악보로 연주하기 전에 코드를 직접 확인해 주세요. 서비스는 음악적·법률적 판단을 대신하지 않습니다.',
    ] },
    { heading: '저작권과 업로드할 수 있는 악보', paragraphs: [
      '악보(가사, 멜로디, 코드 진행, 편곡, 악보 디자인 포함)의 저작권은 작사·작곡·편곡자와 음악 출판사 등 원래 권리자에게 있습니다. Capomatic은 악보에 대한 권리를 갖거나 주장하지 않으며, 사용자에게 권리를 부여하지도 않습니다.',
      '본인이 사용할 권리가 있는 악보만 업로드해 주세요. 예를 들면 직접 만든 악보, 정당하게 구입했거나 이용 허락을 받은 악보, 저작권 보호 기간이 끝난 악보가 해당합니다.',
      '불법으로 복제·유통된 악보나 타인의 개인정보가 담긴 자료는 업로드할 수 없습니다.',
      '업로드한 자료에 필요한 권리를 확보할 책임은 사용자에게 있습니다.',
    ] },
    { heading: '결과물은 개인 연습용으로만', paragraphs: [
      '결과 이미지는 원래 악보에 바뀐 코드를 덧붙인 것이며, 원래 악보의 저작권은 그대로 원래 권리자에게 있습니다.',
      '결과 이미지는 본인의 개인 연습에만 사용해 주세요.',
      '권리자의 허락 없이 단체 채팅방, SNS, 블로그, 카페·커뮤니티에 올리거나, 다른 사람에게 나눠주거나, 판매하거나, 악보집 또는 다른 서비스의 자료로 사용해서는 안 됩니다.',
      '원작자가 다른 조의 공식 악보를 제공한다면 그 악보를 먼저 이용해 주세요.',
    ] },
    { heading: '서비스가 하는 일과 하지 않는 일', paragraphs: [
      'Capomatic은 사용자가 이미 가진 악보에서 코드를 읽고 다른 조로 바꿔 보여주는 도구입니다. 악보를 판매·배포하지 않으며, 악보 검색이나 공유·갤러리 기능이 없습니다.',
      '업로드한 악보는 결과를 만드는 데만 사용되며 업로드한 본인 외에는 누구에게도 보이지 않습니다. 영구 저장소에 보관되지 않고 AI 학습에 사용되지 않습니다. 보관 방식은 개인정보 처리방침을 확인해 주세요.',
      ...(HAS_SUPPORT ? ['후원은 도구의 개발과 운영을 위한 것이며, 악보나 결과물의 대가가 아닙니다.'] : []),
    ] },
    { heading: '권리자 요청', paragraphs: [
      '원작자나 권리자는 아래 문의 경로로 요청할 수 있습니다. 서비스 이용 중단 요청이나 홍보물·예시에서의 제외 요청 등이 해당합니다. 운영자는 요청을 확인한 뒤 빠르게 조치하고 결과를 알려드립니다.',
      '요청에는 다음 내용을 적어 주세요.',
      { list: [
        '권리자 정보와 연락 방법',
        '대상 곡 또는 악보',
        '요청 내용과 확인할 수 있는 정보(예: 결과 이미지가 게시된 위치)',
      ] },
      '서비스에는 악보를 공개 게시하는 기능이 없습니다. 외부에 게시된 결과물은 게시한 사람과 해당 사이트에도 삭제를 요청해야 할 수 있습니다.',
    ] },
    { heading: '위반 시 이용 제한', paragraphs: [
      '저작권을 침해하는 방식으로 서비스를 반복해서 이용하면 운영자는 해당 이용자의 서비스 이용을 제한할 수 있습니다.',
    ] },
    { heading: 'Capomatic의 권리와 안내', paragraphs: [
      'Capomatic의 이름, 로고, 화면 디자인과 소스 코드에 대한 권리는 운영자에게 있습니다.',
      '이 약관은 법률 자문이 아닙니다. 사용할 수 있는지 확실하지 않으면 권리자에게 확인해 주세요.',
    ] },
    { heading: '가용성과 변경', paragraphs: [
      '서비스는 예고 없이 일시 중단되거나 변경될 수 있습니다. 악보와 결과물의 유일한 보관 장소로 사용하지 말고 필요한 파일은 직접 저장해야 합니다.',
    ] },
  ],
  en: [
    { heading: 'The service', paragraphs: [
      'Capomatic is a personal practice tool that detects chords in PNG or JPEG chord sheets and creates transposed or capo-adjusted result images. Use it with sheets you have to find the key and capo position you want to play in.',
      IS_TOSS
        ? 'The Toss mini app works without login and does not save job history.'
        : 'It provides login and browser-specific job history. Administrator features and paid GPT refinement are not part of V1.',
    ] },
    { heading: 'Accuracy and responsibility', paragraphs: [
      'OCR and automatic transpose results may contain omissions or recognition errors. Check the chords yourself before you play from a result sheet. Capomatic does not replace musical or legal judgment.',
    ] },
    { heading: 'Copyright and what you may upload', paragraphs: [
      'Copyright in sheet music (including lyrics, melody, chord progression, arrangement and engraving) belongs to the original rights holders, such as the songwriters, arrangers and music publishers. Capomatic does not own or claim any rights in sheet music and does not grant you any.',
      'Only upload sheet music you have the right to use, for example sheets you created yourself, sheets you purchased or were licensed to use, and sheets whose copyright has expired.',
      'Do not upload illegally copied or distributed sheet music, or material that contains other people’s personal information.',
      'You are responsible for securing any rights the material you upload requires.',
    ] },
    { heading: 'Results are for your personal practice only', paragraphs: [
      'A result image is the original sheet with changed chords added. Copyright in the original sheet stays with its rights holders.',
      'Use result images only for your own personal practice.',
      'You may not, without the rights holder’s permission, post result images to group chats, social media, blogs or online communities, give them to other people, sell them, or use them in songbooks or as material for another service.',
      'If the creator offers an official sheet in another key, please use that sheet first.',
    ] },
    { heading: 'What the service does and does not do', paragraphs: [
      'Capomatic is a tool that reads chords from sheet music you already have and shows them in another key. It does not sell or distribute sheet music, and it has no sheet music search, sharing or gallery features.',
      'Uploaded sheets are used only to produce your result and are never shown to anyone except you. They are not kept in permanent storage and are not used for AI training. See the Privacy Policy for how they are retained.',
      ...(HAS_SUPPORT ? ['Support payments go towards developing and running the tool. They are not payment for sheet music or results.'] : []),
    ] },
    { heading: 'Requests from rights holders', paragraphs: [
      'Creators and rights holders can contact us through the channel below, for example to ask us to stop the service being used for a work, or to be left out of promotional material or examples. We will review the request, act on it promptly and tell you the outcome.',
      'Please include:',
      { list: [
        'who you are and how to reach you;',
        'the song or sheet concerned;',
        'what you are asking for, with information we can check (for example, where a result image was posted).',
      ] },
      'The service has no feature for posting sheets publicly. For results posted elsewhere, you may also need to ask the person who posted them, and the site hosting them, to remove them.',
    ] },
    { heading: 'Restricting access after violations', paragraphs: [
      'If someone repeatedly uses the service in ways that infringe copyright, we may restrict their use of the service.',
    ] },
    { heading: 'Capomatic’s rights and this notice', paragraphs: [
      'Rights in the Capomatic name, logo, interface design and source code belong to the operator.',
      'These terms are not legal advice. If you are unsure whether you may use a piece of music, check with the rights holder.',
    ] },
    { heading: 'Availability and changes', paragraphs: [
      'The service may be interrupted or changed without notice. Do not use it as the only storage location for a sheet or result; save files you need.',
    ] },
  ],
};

export default function TermsPage() {
  return <LegalPage title={{ ko: '이용약관', en: 'Terms of Use' }} sections={sections} updated="2026-10-13" />;
}
