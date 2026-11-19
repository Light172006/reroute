import { describe, it, expect } from 'vitest';
import fs from 'fs';
import path from 'path';

function getAllFiles(dirPath: string, arrayOfFiles: string[] = []): string[] {
  const files = fs.readdirSync(dirPath);

  files.forEach((file) => {
    const fullPath = path.join(dirPath, file);
    if (fs.statSync(fullPath).isDirectory()) {
      getAllFiles(fullPath, arrayOfFiles);
    } else {
      // Check code and asset text files
      if (/\.(ts|tsx|js|jsx|css|json|md)$/.test(file)) {
        arrayOfFiles.push(fullPath);
      }
    }
  });

  return arrayOfFiles;
}

// Regex matching unicode pictographic emojis
const emojiRegex = new RegExp('\\p{Extended_Pictographic}', 'u');

describe('Zero Emoji Enforcement', () => {
  it('should have zero emoji characters in any source file in src/', () => {
    const srcDir = path.resolve(process.cwd(), 'src');
    const allFiles = getAllFiles(srcDir);

    const violations: { file: string; line: number; char: string; snippet: string }[] = [];

    allFiles.forEach((filePath) => {
      // Don't test the no-emoji test file itself if it contains comments or patterns
      if (filePath.endsWith('no-emoji.test.ts')) return;

      const content = fs.readFileSync(filePath, 'utf-8');
      const lines = content.split('\n');

      lines.forEach((lineText, index) => {
        const match = lineText.match(emojiRegex);
        if (match) {
          violations.push({
            file: path.relative(process.cwd(), filePath),
            line: index + 1,
            char: match[0],
            snippet: lineText.trim(),
          });
        }
      });
    });

    if (violations.length > 0) {
      console.error('Emoji violations detected:', violations);
    }

    expect(violations).toEqual([]);
  });
});
