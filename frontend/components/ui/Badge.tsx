import { HTMLAttributes } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info' | 'outline';

interface BadgeProps extends Omit<HTMLMotionProps<'span'>, 'onDrag' | 'onDragStart' | 'onDragEnd'> {
  variant?: BadgeVariant;
  pulse?: boolean;
  className?: string;
  children: React.ReactNode;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-100 text-gray-800',
  success: 'bg-green-100 text-green-800',
  warning: 'bg-yellow-100 text-yellow-800',
  error: 'bg-red-100 text-red-800',
  info: 'bg-blue-100 text-blue-800',
  outline: 'bg-transparent text-gray-700 border border-gray-300',
};

export function Badge({
  children,
  variant = 'default',
  className = '',
  pulse = false,
  ...props
}: BadgeProps) {
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${variantStyles[variant]} ${className}`}
      {...props}
    >
      {pulse && (
        <span className="relative flex h-2 w-2 mr-1.5">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-current opacity-75"></span>
          <span className="relative inline-flex rounded-full h-2 w-2 bg-current"></span>
        </span>
      )}
      {children}
    </motion.span>
  );
}

type StatusType = 'idle' | 'connecting' | 'connected' | 'error';

type StatusMap = {
  [key in StatusType]: {
    text: string;
    variant: BadgeVariant;
    pulse?: boolean;
  };
};

export function StatusBadge({ status }: { status: StatusType }) {
  const statusMap: StatusMap = {
    idle: { text: 'Idle', variant: 'default' },
    connecting: { text: 'Connecting...', variant: 'warning', pulse: true },
    connected: { text: 'Connected', variant: 'success' },
    error: { text: 'Error', variant: 'error' },
  };

  const { text, variant, pulse = false } = statusMap[status];

  return (
    <Badge variant={variant} pulse={pulse}>
      {text}
    </Badge>
  );
}
