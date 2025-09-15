import { InputHTMLAttributes, TextareaHTMLAttributes, forwardRef, useState, FocusEvent } from 'react';
import { motion, HTMLMotionProps } from 'framer-motion';

type InputVariant = 'default' | 'filled' | 'outline' | 'underline';
type InputSize = 'sm' | 'md' | 'lg';

interface InputProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'size'> {
  /** Visual style variant */
  variant?: InputVariant;
  /** Size of the input */
  size?: InputSize;
  /** Whether the input has an error */
  error?: boolean;
  /** Optional label text */
  label?: string;
  /** Optional helper/error message */
  message?: string;
  /** Optional leading icon */
  leftIcon?: React.ReactNode;
  /** Optional trailing icon */
  rightIcon?: React.ReactNode;
  /** Optional class name for the container */
  containerClassName?: string;
  /** Whether to show a character counter */
  showCounter?: boolean;
  /** Maximum length for the counter */
  maxLength?: number;
}

const inputVariants = {
  default: 'bg-white border border-gray-200 hover:border-gray-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-100',
  filled: 'bg-gray-50 border border-transparent hover:bg-gray-100 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-100',
  outline: 'bg-transparent border border-gray-300 hover:border-gray-400 focus:border-blue-500 focus:ring-2 focus:ring-blue-100',
  underline: 'bg-transparent border-0 border-b-2 border-gray-200 rounded-none px-0 focus:border-blue-500 focus:ring-0',
};

const inputSizes = {
  sm: 'h-8 px-2.5 text-sm',
  md: 'h-10 px-3.5 text-base',
  lg: 'h-12 px-4 text-lg',
};

const labelSizes = {
  sm: 'text-xs mb-1',
  md: 'text-sm mb-1.5',
  lg: 'text-base mb-2',
};

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({
    className = '',
    variant = 'default',
    size = 'md',
    error = false,
    label,
    message,
    leftIcon,
    rightIcon,
    containerClassName = '',
    showCounter = false,
    maxLength,
    onFocus,
    onBlur,
    ...props
  }, ref) => {
    const [isFocused, setIsFocused] = useState(false);
    const currentLength = props.value?.toString().length || 0;

    const handleFocus = (e: FocusEvent<HTMLInputElement>) => {
      setIsFocused(true);
      onFocus?.(e);
    };

    const handleBlur = (e: FocusEvent<HTMLInputElement>) => {
      setIsFocused(false);
      onBlur?.(e);
    };

    const inputClasses = [
      'w-full transition-all duration-200 rounded-lg outline-none',
      inputVariants[variant],
      inputSizes[size],
      error ? 'border-red-500 focus:border-red-500 focus:ring-red-100' : '',
      leftIcon ? 'pl-10' : '',
      rightIcon ? 'pr-10' : '',
      props.disabled ? 'opacity-60 cursor-not-allowed' : '',
      className,
    ].filter(Boolean).join(' ');

    return (
      <div className={`w-full ${containerClassName}`}>
        {label && (
          <label 
            className={`block font-medium text-gray-700 ${labelSizes[size]} ${
              error ? 'text-red-600' : ''
            }`}
          >
            {label}
          </label>
        )}
        <div className="relative">
          {leftIcon && (
            <div className={`absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 ${
              isFocused ? 'text-blue-500' : ''
            }`}>
              {leftIcon}
            </div>
          )}
          <input
            ref={ref}
            className={inputClasses}
            onFocus={handleFocus}
            onBlur={handleBlur}
            maxLength={maxLength}
            {...props}
          />
          {rightIcon && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              {rightIcon}
            </div>
          )}
        </div>
        {(message || showCounter) && (
          <div className="mt-1.5 flex justify-between items-center">
            {message && (
              <p className={`text-sm ${error ? 'text-red-600' : 'text-gray-500'}`}>
                {message}
              </p>
            )}
            {showCounter && maxLength && (
              <span className="text-xs text-gray-400">
                {currentLength}/{maxLength}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  /** Visual style variant */
  variant?: InputVariant;
  /** Size of the textarea */
  size?: InputSize;
  /** Whether the textarea has an error */
  error?: boolean;
  /** Optional label text */
  label?: string;
  /** Optional helper/error message */
  message?: string;
  /** Whether to auto-resize the textarea */
  autoResize?: boolean;
  /** Whether to show a character counter */
  showCounter?: boolean;
  /** Optional class name for the container */
  containerClassName?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({
    className = '',
    variant = 'default',
    size = 'md',
    error = false,
    label,
    message,
    autoResize = true,
    showCounter = false,
    maxLength,
    containerClassName = '',
    onInput,
    ...props
  }, ref) => {
    const [currentLength, setCurrentLength] = useState(
      props.defaultValue?.toString().length || props.value?.toString().length || 0
    );

    const handleInput = (e: React.FormEvent<HTMLTextAreaElement>) => {
      if (autoResize) {
        const target = e.target as HTMLTextAreaElement;
        target.style.height = 'auto';
        target.style.height = `${target.scrollHeight}px`;
      }
      
      if (onInput) {
        onInput(e);
      }

      setCurrentLength(e.currentTarget.value.length);
    };

    const textareaClasses = [
      'w-full transition-all duration-200 rounded-lg outline-none resize-none',
      inputVariants[variant],
      size === 'sm' ? 'py-1.5 px-2.5 text-sm' : size === 'lg' ? 'py-3 px-4 text-lg' : 'py-2 px-3 text-base',
      error ? 'border-red-500 focus:border-red-500 focus:ring-red-100' : '',
      props.disabled ? 'opacity-60 cursor-not-allowed' : '',
      className,
    ].filter(Boolean).join(' ');

    return (
      <div className={`w-full ${containerClassName}`}>
        {label && (
          <label 
            className={`block font-medium text-gray-700 ${labelSizes[size]} ${
              error ? 'text-red-600' : ''
            }`}
          >
            {label}
          </label>
        )}
        <div className="relative">
          <textarea
            ref={ref}
            className={textareaClasses}
            onInput={handleInput}
            maxLength={maxLength}
            {...props}
          />
        </div>
        {(message || showCounter) && (
          <div className="mt-1.5 flex justify-between items-center">
            {message && (
              <p className={`text-sm ${error ? 'text-red-600' : 'text-gray-500'}`}>
                {message}
              </p>
            )}
            {showCounter && maxLength && (
              <span className="text-xs text-gray-400">
                {currentLength}/{maxLength}
              </span>
            )}
          </div>
        )}
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';


