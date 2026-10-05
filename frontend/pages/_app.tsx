import Head from "next/head";
import type { AppProps } from "next/app";
import { Analytics } from "@vercel/analytics/next";
import { AuthProvider } from "@/components/AuthProvider";
import { LangProvider } from "@/components/LangProvider";
import "@/styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <LangProvider>
      <Head>
        <meta name="viewport" content={process.env.NEXT_PUBLIC_APP_TARGET === 'toss'
          ? 'width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no'
          : 'width=device-width, initial-scale=1'} />
      </Head>
      <AuthProvider>
        <Component {...pageProps} />
        {process.env.NEXT_PUBLIC_APP_TARGET !== 'toss' && <Analytics />}
      </AuthProvider>
    </LangProvider>
  );
}
