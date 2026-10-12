import NextErrorComponent, { ErrorProps } from 'next/error';
import * as Sentry from '@sentry/nextjs';

export default function ErrorPage(props: ErrorProps) {
  return <NextErrorComponent statusCode={props.statusCode} withDarkMode={process.env.NEXT_PUBLIC_APP_TARGET !== 'toss'} />;
}

ErrorPage.getInitialProps = async (contextData: Parameters<typeof NextErrorComponent.getInitialProps>[0]) => {
  await Sentry.captureUnderscoreErrorException(contextData);
  return NextErrorComponent.getInitialProps(contextData);
};
