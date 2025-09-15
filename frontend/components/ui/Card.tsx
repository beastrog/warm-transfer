import { HTMLAttributes, forwardRef } from 'react';
import { motion, Variants } from 'framer-motion';

type CardVariant = 'elevated' | 'filled' | 'outlined';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant;
  initial?: 'hidden' | 'visible' | 'exit';
  animate?: 'hidden' | 'visible' | 'exit';
  exit?: 'hidden' | 'visible' | 'exit';
  transition?: {
    type?: string;
    stiffness?: number;
    damping?: number;
    duration?: number;
  };
}

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -20 }
};

const variantStyles: Record<CardVariant, string> = {
  elevated: 'bg-white shadow-md rounded-xl border border-gray-100',
  filled: 'bg-gray-50 rounded-xl border border-gray-200',
  outlined: 'bg-white rounded-xl border border-gray-200',
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({
    className = '',
    variant = 'elevated',
    initial = 'hidden',
    animate = 'visible',
    exit = 'exit',
    transition = { duration: 0.3 },
    ...props
  }, ref) => {
    return (
      <motion.div
        ref={ref}
        initial={initial}
        animate={animate}
        exit={exit}
        variants={cardVariants}
        transition={transition}
        className={`${variantStyles[variant]} ${className}`}
        {...props}
      />
    );
  }
);

Card.displayName = 'Card';

export const CardHeader = ({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={`p-6 pb-0 ${className}`} {...props} />
);

export const CardTitle = ({ className = '', ...props }: HTMLAttributes<HTMLHeadingElement>) => (
  <h3 className={`text-lg font-semibold text-gray-900 ${className}`} {...props} />
);

export const CardDescription = ({ className = '', ...props }: HTMLAttributes<HTMLParagraphElement>) => (
  <p className={`mt-1 text-sm text-gray-500 ${className}`} {...props} />
);

export const CardContent = ({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={`p-6 pt-0 ${className}`} {...props} />
);

export const CardFooter = ({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) => (
  <div className={`flex items-center p-6 pt-0 ${className}`} {...props} />
);
