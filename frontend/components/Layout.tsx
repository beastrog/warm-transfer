import { HTMLAttributes } from 'react';

export default function Layout({ className = '', ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={`min-h-screen ${className}`} {...props} />
  );
}


