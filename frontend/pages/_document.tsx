import { Head, Html, Main, NextScript } from 'next/document';

export default function Document() {
  return (
    <Html lang="ko" data-app-target={process.env.NEXT_PUBLIC_APP_TARGET}>
      <Head><meta name="color-scheme" content="light" /></Head>
      <body>
        <Main />
        <NextScript />
      </body>
    </Html>
  );
}
