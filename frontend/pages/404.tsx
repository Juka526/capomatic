import NextError from 'next/error';
import { useRouter } from 'next/router';
import { useTossBack } from '@/lib/toss';

export default function NotFoundPage() {
  const router = useRouter();
  useTossBack(() => { void router.replace('/'); return true; });
  return <NextError statusCode={404} withDarkMode={process.env.NEXT_PUBLIC_APP_TARGET !== 'toss'} />;
}
