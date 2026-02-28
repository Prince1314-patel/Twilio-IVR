/**
 * Utility Helper Functions
 * ========================
 * 
 * Shared utility functions used across the application.
 */

import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Merges Tailwind CSS classes with clsx and tailwind-merge.
 * 
 * @param inputs - Class values to merge
 * @returns Merged class string
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Formats a phone number for display.
 * 
 * @param phoneNumber - Phone number in E.164 format
 * @returns Formatted phone number string
 */
export function formatPhoneNumber(phoneNumber: string): string {
  if (!phoneNumber) return '';
  // Remove + and format
  const cleaned = phoneNumber.replace(/[^\d]/g, '');
  if (cleaned.length <= 3) return phoneNumber;
  if (cleaned.length <= 6) return `+${cleaned.slice(0, 3)} ${cleaned.slice(3)}`;
  if (cleaned.length <= 10) return `+${cleaned.slice(0, 3)} ${cleaned.slice(3, 6)} ${cleaned.slice(6)}`;
  return `+${cleaned.slice(0, cleaned.length - 10)} (${cleaned.slice(cleaned.length - 10, cleaned.length - 7)}) ${cleaned.slice(cleaned.length - 7, cleaned.length - 4)}-${cleaned.slice(cleaned.length - 4)}`;
}

/**
 * Validates a phone number in E.164 format.
 * 
 * @param phoneNumber - Phone number to validate
 * @returns True if valid, false otherwise
 */
export function validatePhoneNumber(phoneNumber: string): boolean {
  return /^\+[1-9]\d{1,14}$/.test(phoneNumber);
}

/**
 * Truncates text to a maximum length with ellipsis.
 * 
 * @param text - Text to truncate
 * @param maxLength - Maximum length
 * @returns Truncated text
 */
export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

