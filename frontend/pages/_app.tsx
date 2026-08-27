import type { AppProps } from "next/app";
import { AuthProvider } from "@/components/AuthProvider";
import { LangProvider } from "@/components/LangProvider";
import { Analytics } from "@vercel/analytics/next";
import "@/styles/globals.css";

export default function App({ Component, pageProps }: AppProps) {
  return (
    <LangProvider>
      <AuthProvider>
        <Component {...pageProps} />
        <Analytics />
      </AuthProvider>
    </LangProvider>
  );
}
