import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  const d = typeof date === 'string' ? new Date(date) : date
  return d.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
}

export function formatNumber(num: number | string | null | undefined): string {
  if (num === null || num === undefined) return 'N/A'
  const n = typeof num === 'string' ? parseFloat(num) : num
  if (isNaN(n)) return 'N/A'
  return new Intl.NumberFormat('en-IN').format(n)
}

export function formatCurrency(amount: number | string | null | undefined, currency: string = 'INR'): string {
  if (amount === null || amount === undefined) return 'N/A'
  const n = typeof amount === 'string' ? parseFloat(amount) : amount
  if (isNaN(n)) return 'N/A'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}
