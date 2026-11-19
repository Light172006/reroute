import '@testing-library/jest-dom';

const originalError = console.error;
const originalWarn = console.warn;

console.error = (...args: unknown[]) => {
  originalError(...args);
  const message = args.map((a) => (typeof a === 'string' ? a : String(a))).join(' ');
  throw new Error(`Unexpected console.error during test: ${message}`);
};

console.warn = (...args: unknown[]) => {
  originalWarn(...args);
  const message = args.map((a) => (typeof a === 'string' ? a : String(a))).join(' ');
  if (
    message.toLowerCase().includes('key') ||
    message.toLowerCase().includes('hydration') ||
    message.toLowerCase().includes('validatedomnesting')
  ) {
    throw new Error(`Unexpected React warning during test: ${message}`);
  }
};
