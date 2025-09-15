import { ButtonHTMLAttributes, ReactNode, forwardRef } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'link' | 'danger';
export type ButtonSize = 'sm' | 'md' | 'lg';

interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag' | 'style'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
  children: ReactNode;
}

const baseStyles = 'inline-flex items-center justify-center font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:pointer-events-none';

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-blue-600 text-white hover:bg-blue-700 focus:ring-blue-500',
  secondary: 'bg-gray-100 text-gray-900 hover:bg-gray-200 focus:ring-gray-500',
  outline: 'bg-transparent border border-gray-300 text-gray-700 hover:bg-gray-50 focus:ring-blue-500',
  ghost: 'bg-transparent text-gray-700 hover:bg-gray-100 focus:ring-blue-500',
  link: 'bg-transparent text-blue-600 hover:underline p-0 h-auto',
  danger: 'bg-red-600 text-white hover:bg-red-700 focus:ring-red-500',
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-sm rounded-lg',
  md: 'h-10 px-4 py-2 rounded-xl',
  lg: 'h-12 px-6 text-lg rounded-xl',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    variant = 'primary',
    size = 'md',
    fullWidth = false,
    loading = false,
    leftIcon,
    rightIcon,
    className = '',
    children,
    disabled,
    ...props
  }, ref) => {
    const isDisabled = disabled || loading;
    
    return (
      <motion.button
        ref={ref}
        className={`
          ${baseStyles}
          ${variantStyles[variant]}
          ${sizeStyles[size]}
          ${fullWidth ? 'w-full' : ''}
          ${isDisabled ? 'opacity-70 cursor-not-allowed' : 'cursor-pointer'}
          ${className}
        `}
        disabled={isDisabled}
        whileTap={!isDisabled ? { scale: 0.98 } : undefined}
        whileHover={!isDisabled ? { y: -1 } : undefined}
        {...props}
      >
        {loading ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {children}
          </>
        ) : (
          <>
            {leftIcon && <span className="mr-2">{leftIcon}</span>}
            {children}
            {rightIcon && <span className="ml-2">{rightIcon}</span>}
          </>
        )}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';

// Button with icon component
type ButtonIconProps = Omit<ButtonProps, 'children'> & {
  icon: ReactNode;
  label: string;
};

export const IconButton = forwardRef<HTMLButtonElement, ButtonIconProps>(
  ({ icon, label, className = '', ...props }, ref) => (
    <Button
      ref={ref}
      aria-label={label}
      className={`p-2 ${className}`}
      variant="ghost"
      size="sm"
      {...props}
    >
      {icon}
    </Button>
  )
);

IconButton.displayName = 'IconButton';
