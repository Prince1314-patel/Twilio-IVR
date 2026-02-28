/**
 * Phone Input Component
 * ====================
 * 
 * Phone number input component with validation.
 */

import React from 'react';
import { Input } from '@/components/ui/input';
import { cn } from '@/utils';
import { validatePhoneNumber } from '@/utils/helpers';

interface PhoneInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
}

export function PhoneInput({
  value,
  onChange,
  placeholder = '+1234567890',
  className,
  disabled = false,
}: PhoneInputProps) {
  const isValid = value ? validatePhoneNumber(value) : true;
  const isEmpty = value.length === 0;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    let newValue = e.target.value;

    // Auto-add + if not present and starts with a digit
    if (newValue.length > 0 && !newValue.startsWith('+') && /^\d/.test(newValue)) {
      newValue = '+' + newValue;
    }

    // Only allow +, digits, and spaces
    newValue = newValue.replace(/[^\d+ ]/g, '');

    onChange(newValue);
  };

  return (
    <div className="relative">
      <Input
        type="tel"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        disabled={disabled}
        className={cn(
          'pr-10',
          !isEmpty && !isValid && 'border-destructive focus-visible:ring-destructive',
          className
        )}
      />
      {!isEmpty && !isValid && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-destructive">
          Invalid
        </span>
      )}
      {!isEmpty && isValid && (
        <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-green-600">
          ✓
        </span>
      )}
    </div>
  );
}

