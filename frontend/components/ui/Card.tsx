import { HTMLAttributes, forwardRef } from 'react';
import { motion, Variants } from 'framer-motion';

type CardVariant = 'elevated' | 'filled' | 'outlined' | 'glass';
type CardRounded = 'sm' | 'md' | 'lg' | 'xl' | '2xl' | 'full' | 'none';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Visual style variant of the card */
  variant?: CardVariant;
  /** Border radius of the card */
  rounded?: CardRounded;
  /** Whether the card should have a hover effect */
  hoverable?: boolean;
  /** Animation variants for Framer Motion */
  initial?: 'hidden' | 'visible' | 'exit' | object;
  animate?: 'hidden' | 'visible' | 'exit' | object;
  exit?: 'hidden' | 'visible' | 'exit' | object;
  /** Animation transition */
  transition?: {
    type?: string;
    stiffness?: number;
    damping?: number;
    duration?: number;
    delay?: number;
  };
  /** Whether to disable animations */
  disableAnimation?: boolean;
}

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 12, scale: 0.98 },
  visible: { 
    opacity: 1, 
    y: 0, 
    scale: 1,
    transition: { 
      type: 'spring', 
      stiffness: 400, 
      damping: 25,
      duration: 0.3 
    } 
  },
  exit: { 
    opacity: 0, 
    y: -12, 
    scale: 0.98,
    transition: { 
      duration: 0.15 
    } 
  }
};

const variantStyles: Record<CardVariant, string> = {
  elevated: 'bg-white shadow-sm hover:shadow-md border border-gray-100',
  filled: 'bg-gray-50 border border-gray-100',
  outlined: 'bg-white border border-gray-200',
  glass: 'backdrop-blur-md bg-white/70 border border-white/20 shadow-lg',
};

const roundedStyles: Record<CardRounded, string> = {
  none: 'rounded-none',
  sm: 'rounded-sm',
  md: 'rounded-lg',
  lg: 'rounded-xl',
  xl: 'rounded-2xl',
  '2xl': 'rounded-3xl',
  full: 'rounded-full',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({
    className = '',
    variant = 'elevated',
    rounded = 'lg',
    hoverable = true,
    initial = 'hidden',
    animate = 'visible',
    exit = 'exit',
    transition = { 
      type: 'spring',
      stiffness: 400,
      damping: 25,
      duration: 0.3 
    },
    disableAnimation = false,
    ...props
  }, ref) => {
    const baseStyles = [
      'overflow-hidden transition-all duration-200',
      variantStyles[variant],
      roundedStyles[rounded],
      hoverable && 'hover:shadow-md hover:-translate-y-0.5',
      className
    ].filter(Boolean).join(' ');

    if (disableAnimation) {
      return <div ref={ref} className={baseStyles} {...props} />;
    }

    return (
      <motion.div
        ref={ref}
        initial={typeof initial === 'string' ? initial : { ...initial }}
        animate={typeof animate === 'string' ? animate : { ...animate }}
        exit={typeof exit === 'string' ? exit : { ...exit }}
        variants={cardVariants}
        transition={transition}
        className={baseStyles}
        whileHover={hoverable ? { 
          y: -2,
          boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1)'
        } : {}}
        {...props}
      />
    );
  }
);

Card.displayName = 'Card';

interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  /** Additional class name for the header */
  className?: string;
  /** Whether to add padding to the header */
  noPadding?: boolean;
}

export function CardHeader({ 
  className = '', 
  noPadding = false, 
  ...props 
}: CardHeaderProps) {
  return (
    <div 
      className={`flex flex-col space-y-1.5 ${!noPadding ? 'p-6 pb-2' : ''} ${className}`} 
      {...props} 
    />
  );
}

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  /** Heading level (h1-h6) */
  as?: 'h1' | 'h2' | 'h3' | 'h4' | 'h5' | 'h6';
  /** Additional class name */
  className?: string;
}

export function CardTitle({ 
  as: Tag = 'h3', 
  className = '', 
  ...props 
}: CardTitleProps) {
  return (
    <Tag 
      className={`text-xl font-semibold leading-tight tracking-tight text-gray-900 ${className}`} 
      {...props} 
    />
  );
}

interface CardDescriptionProps extends HTMLAttributes<HTMLParagraphElement> {
  /** Additional class name */
  className?: string;
  /** Text color variant */
  variant?: 'default' | 'muted' | 'subtle';
}

export function CardDescription({ 
  className = '', 
  variant = 'muted',
  ...props 
}: CardDescriptionProps) {
  const variantClasses = {
    default: 'text-gray-900',
    muted: 'text-gray-600',
    subtle: 'text-gray-400',
  };
  
  return (
    <p 
      className={`text-sm ${variantClasses[variant]} ${className}`} 
      {...props} 
    />
  );
}

interface CardContentProps extends HTMLAttributes<HTMLDivElement> {
  /** Additional class name */
  className?: string;
  /** Whether to add padding */
  noPadding?: boolean;
}

export function CardContent({ 
  className = '', 
  noPadding = false, 
  ...props 
}: CardContentProps) {
  return (
    <div 
      className={`${!noPadding ? 'p-6' : ''} ${className}`} 
      {...props} 
    />
  );
}

interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  /** Additional class name */
  className?: string;
  /** Whether to add padding */
  noPadding?: boolean;
  /** Flex direction */
  direction?: 'row' | 'col';
  /** Items alignment */
  align?: 'start' | 'center' | 'end' | 'between' | 'around' | 'evenly';
}

export function CardFooter({ 
  className = '', 
  noPadding = false, 
  direction = 'row',
  align = 'between',
  ...props 
}: CardFooterProps) {
  const directionClass = direction === 'col' ? 'flex-col space-y-2' : 'flex-row space-x-3';
  const alignClasses = {
    start: 'justify-start',
    center: 'justify-center',
    end: 'justify-end',
    between: 'justify-between',
    around: 'justify-around',
    evenly: 'justify-evenly',
  };
  
  return (
    <div 
      className={`flex ${directionClass} ${alignClasses[align]} ${!noPadding ? 'p-6 pt-0' : ''} ${className}`} 
      {...props} 
    />
  );
}
