import type { AppProps } from 'next/app';
import { useRouter } from 'next/router';
import { useEffect } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { ToastProvider } from '../components/ui/Toast';
import Head from 'next/head';
import '../styles/globals.css';

// Custom App with page transitions and global providers
function App({ Component, pageProps, router }: AppProps & { router: any }) {
  // Handle route changes for page transitions
  const { pathname } = useRouter();
  
  // Add smooth scroll behavior
  useEffect(() => {
    if (typeof window !== 'undefined') {
      window.scrollTo(0, 0);
    }
  }, [pathname]);

  return (
    <>
      <Head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0" />
        <meta name="theme-color" content="#3b82f6" />
        <title>Warm Transfer</title>
        <link rel="icon" href="/favicon.ico" />
      </Head>
      
      <ToastProvider>
        <AnimatePresence mode="wait">
          <motion.div
            key={router.route}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="min-h-screen flex flex-col"
          >
            <Component {...pageProps} />
          </motion.div>
        </AnimatePresence>
      </ToastProvider>
    </>
  );
}

export default App;
