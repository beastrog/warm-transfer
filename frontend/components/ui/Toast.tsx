import { createContext, useContext, useMemo, useState, ReactNode, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { Button } from './Button';

type ToastVariant = 'success' | 'error' | 'info' | 'warning';

export interface Toast {
  id: number;
  title: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

type ToastContextType = {
  toasts: Toast[];
  toast: (props: Omit<Toast, 'id'>) => void;
  removeToast: (id: number) => void;
};

const ToastContext = createContext<ToastContextType>({
  toasts: [],
  toast: () => {},
  removeToast: () => {},
});

const toastVariants = {
  success: {
    bg: 'bg-green-50',
    border: 'border-green-500',
    icon: '✅',
  },
  error: {
    bg: 'bg-red-50',
    border: 'border-red-500',
    icon: '❌',
  },
  warning: {
    bg: 'bg-yellow-50',
    border: 'border-yellow-500',
    icon: '⚠️',
  },
  info: {
    bg: 'bg-blue-50',
    border: 'border-blue-500',
    icon: 'ℹ️',
  },
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const removeToast = useCallback((id: number) => {
    setToasts((currentToasts) =>
      currentToasts.filter((toast) => toast.id !== id)
    );
  }, []);

  const toast = useCallback(
    (props: Omit<Toast, 'id'>) => {
      // Use a combination of Date.now() and Math.random() to ensure uniqueness
      const id = Date.now() + Math.floor(Math.random() * 1000000);
      const duration = props.duration ?? 5000;

      setToasts((currentToasts) => [...currentToasts, { ...props, id }]);

      if (duration > 0) {
        setTimeout(() => removeToast(id), duration);
      }
    },
    [removeToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, toast, removeToast }}>
      {children}
      <AnimatePresence>
        <div className="fixed top-4 right-4 z-50 space-y-2">
          {toasts.map((toast) => (
            <motion.div
              key={toast.id}
              layout
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -20, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className={`relative flex w-80 flex-col rounded-lg border-l-4 p-4 shadow-lg ${
                toastVariants[toast.variant || 'info'].bg
              } ${toastVariants[toast.variant || 'info'].border}`}
              role="alert"
            >
              <div className="flex items-start">
                <span className="mr-2 text-lg">
                  {toastVariants[toast.variant || 'info'].icon}
                </span>
                <div className="flex-1">
                  <h3 className="text-sm font-medium text-gray-900">
                    {toast.title}
                  </h3>
                  {toast.description && (
                    <p className="mt-1 text-sm text-gray-600">
                      {toast.description}
                    </p>
                  )}
                  {toast.action && (
                    <div className="mt-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => {
                          toast.action?.onClick();
                          removeToast(toast.id);
                        }}
                        className="text-xs"
                      >
                        {toast.action.label}
                      </Button>
                    </div>
                  )}
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => removeToast(toast.id)}
                  className="absolute right-1 top-1 h-6 w-6 p-0"
                  aria-label="Close"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </motion.div>
          ))}
        </div>
      </AnimatePresence>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const context = useContext(ToastContext);
  if (context === undefined) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}

export function useToastHook() {
  const { toast } = useToast();
  return toast;
}
