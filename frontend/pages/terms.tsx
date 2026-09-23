import LegalPage from '@/components/LegalPage';

const sections = {
  ko: [
    { heading: '서비스', paragraphs: [
      'Capomatic은 PNG·JPEG 코드 악보에서 코드를 감지하고 전조·카포 조정 결과 이미지를 만드는 도구입니다. 로그인과 브라우저별 작업 기록을 제공하지만, V1에는 관리자 기능이나 유료 GPT 보정이 포함되지 않습니다.',
    ] },
    { heading: '정확도와 사용 책임', paragraphs: [
      'OCR과 자동 전조 결과에는 누락이나 오인식이 있을 수 있습니다. 공연, 예배 또는 배포 전에 사용자가 코드와 결과 악보를 직접 확인해야 합니다. 서비스는 음악적·법률적 판단을 대신하지 않습니다.',
    ] },
    { heading: '업로드할 수 있는 자료', paragraphs: [
      '본인이 사용할 권리가 있는 악보만 업로드해야 하며, 불법 자료나 타인의 개인정보가 포함된 자료를 업로드해서는 안 됩니다. 업로드한 자료에 필요한 권리를 확보할 책임은 사용자에게 있습니다.',
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
    { heading: 'What you may upload', paragraphs: [
      'Upload only sheets that you have the right to use. Do not upload unlawful material or content containing another person’s private information. You are responsible for securing the rights needed for material you submit.',
    ] },
    { heading: 'Availability and changes', paragraphs: [
      'The service may be interrupted or changed without notice. Do not use it as the only storage location for a sheet or result; save files you need.',
    ] },
  ],
};

export default function TermsPage() {
  return <LegalPage title={{ ko: '이용약관', en: 'Terms of Use' }} sections={sections} />;
}
