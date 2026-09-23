import NextErrorComponent, { ErrorProps } from 'next/error';
import * as Sentry from '@sentry/nextjs';

export default function ErrorPage(props: ErrorProps) {
  return <NextErrorComponent statusCode={props.statusCode} />;
}

ErrorPage.getInitialProps = async (contextData: Parameters<typeof NextErrorComponent.getInitialProps>[0]) => {
  await Sentry.captureUnderscoreErrorException(contextData);
  return NextErrorComponent.getInitialProps(contextData);
};
