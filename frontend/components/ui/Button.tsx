import { ButtonHTMLAttributes, ReactNode, forwardRef } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';
import { Loader2 } from 'lucide-react';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'link' | 'danger' | 'success';
export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg';

interface ButtonProps extends Omit<HTMLMotionProps<'button'>, 'onAnimationStart' | 'onDragStart' | 'onDragEnd' | 'onDrag' | 'style'> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  fullWidth?: boolean;
  loading?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  className?: string;
  children: ReactNode;
  rounded?: 'sm' | 'md' | 'lg' | 'full';
  shadow?: 'sm' | 'md' | 'lg' | 'none' | 'inner';
}

const baseStyles = 'inline-flex items-center justify-center font-medium transition-all duration-200 ease-out focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-60 disabled:pointer-events-none';

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-[var(--primary)] text-white hover:bg-[var(--primary-hover)] focus:ring-[var(--primary)] focus:ring-offset-1',
  secondary: 'bg-[var(--secondary)] text-white hover:bg-opacity-90 focus:ring-[var(--secondary)] focus:ring-offset-1',
  outline: 'bg-transparent border border-[var(--border)] text-[var(--text)] hover:bg-gray-50 focus:ring-gray-300',
  ghost: 'bg-transparent text-[var(--text)] hover:bg-gray-100 focus:ring-gray-200',
  link: 'bg-transparent text-[var(--primary)] hover:underline p-0 h-auto focus:ring-0 focus:ring-offset-0',
  danger: 'bg-red-500 text-white hover:bg-red-600 focus:ring-red-300',
  success: 'bg-green-500 text-white hover:bg-green-600 focus:ring-green-300',
};

const sizeStyles: Record<ButtonSize, string> = {
  xs: 'h-7 px-3 text-xs rounded-lg',
  sm: 'h-9 px-4 text-sm rounded-xl',
  md: 'h-11 px-5 text-base rounded-xl',
  lg: 'h-14 px-7 text-lg rounded-xl',
};

const roundedStyles = {
  sm: 'rounded',
  md: 'rounded-xl',
  lg: 'rounded-2xl',
  full: 'rounded-full',
};

const shadowStyles = {
  none: 'shadow-none',
  sm: 'shadow-sm',
  md: 'shadow',
  lg: 'shadow-lg',
  inner: 'shadow-inner',
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
    rounded = 'md',
    shadow = 'sm',
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
          ${roundedStyles[rounded]}
          ${shadow !== 'none' ? shadowStyles[shadow] : ''}
          ${fullWidth ? 'w-full' : 'w-auto'}
          ${className}
        `.trim()}
        disabled={isDisabled}
        whileTap={{ scale: isDisabled ? 1 : 0.98 }}
        whileHover={isDisabled ? {} : { y: -1, boxShadow: '0 4px 12px -2px rgba(0, 0, 0, 0.1)' }}
        transition={{ duration: 0.2, ease: 'easeOut' }}
        {...props}
      >
        {loading && (
          <motion.span 
            className="mr-2"
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -5 }}
          >
            <Loader2 className="h-4 w-4 animate-spin" />
          </motion.span>
        )}
        {!loading && leftIcon && (
          <motion.span 
            className="mr-2"
            initial={{ opacity: 0, x: -5 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -5 }}
          >
            {leftIcon}
          </motion.span>
        )}
        <motion.span
          className="whitespace-nowrap"
          initial={{ opacity: loading ? 0 : 1, y: loading ? 2 : 0 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -2 }}
          transition={{ duration: 0.15 }}
        >
          {children}
        </motion.span>
        {!loading && rightIcon && (
          <motion.span 
            className="ml-2"
            initial={{ opacity: 0, x: 5 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 5 }}
          >
            {rightIcon}
          </motion.span>
        )}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';

// Button with icon component
interface ButtonIconProps extends Omit<ButtonProps, 'children'> {
  /** Icon component to render */
  icon: ReactNode;
  /** Accessible label for the button */
  'aria-label': string;
  /** Optional tooltip text */
  title?: string;
}

export const IconButton = forwardRef<HTMLButtonElement, ButtonIconProps>(
  ({ 
    icon, 
    className = '', 
    size = 'md',
    variant = 'ghost',
    rounded = 'full',
    shadow = 'none',
    ...props 
  }, ref) => {
    const iconSizes = {
      xs: 'h-8 w-8 p-1.5',
      sm: 'h-10 w-10 p-2',
      md: 'h-12 w-12 p-3',
      lg: 'h-14 w-14 p-3.5',
    };

    return (
      <Button
        ref={ref}
        variant={variant}
        size={size}
        rounded={rounded}
        shadow={shadow}
        className={`p-0 ${iconSizes[size]} ${className}`}
        {...props}
      >
        {icon}
      </Button>
    );
  }
);

IconButton.displayName = 'IconButton';
