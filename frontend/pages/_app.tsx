import type { AppProps } from 'next/app';
import '../styles/globals.css';
import { AnimatePresence } from 'framer-motion';
import { ToastProvider } from '../components/ui/Toast';

export default function MyApp({ Component, pageProps, router }: AppProps & { router: any }) {
  return (
    <ToastProvider>
      <AnimatePresence mode="wait">
        <Component key={(router as any)?.route} {...pageProps} />
      </AnimatePresence>
    </ToastProvider>
  );
}
