import React, { useEffect, useState } from 'react';
import { Check, Copy, X } from 'lucide-react';
import { DakSkillSpec } from '../data/dakPlugin';

interface SkillDetailModalProps {
  skill: DakSkillSpec | null;
  onClose: () => void;
}

type CalloutKind = 'IMPORTANT' | 'CAUTION' | 'WARNING' | 'NOTE' | 'TIP';

type MarkdownBlock =
  | { type: 'heading'; level: number; text: string }
  | { type: 'paragraph'; text: string }
  | { type: 'code'; lang: string; code: string }
  | { type: 'list'; ordered: boolean; items: string[] }
  | { type: 'callout'; kind: CalloutKind; blocks: MarkdownBlock[] }
  | { type: 'blockquote'; blocks: MarkdownBlock[] }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'hr' };

function parseInlineMarkdown(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const regex =
    /(`[^`]+`|\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\)|(?<!\*)\*(?!\s)[^*]+?(?<!\s)\*(?!\*))/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let keyIdx = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith('`') && token.endsWith('`')) {
      nodes.push(
        <code
          key={keyIdx++}
          className="font-mono text-[12px] bg-[#EEF2F6] text-[#1E3A5F] px-1.5 py-[1px] rounded-[5px]"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith('**') && token.endsWith('**')) {
      nodes.push(
        <strong key={keyIdx++} className="font-semibold text-[#1F1F1F]">
          {parseInlineMarkdown(token.slice(2, -2))}
        </strong>
      );
    } else if (token.startsWith('[')) {
      const linkMatch = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        const isHttp = /^https?:\/\//i.test(linkMatch[2]);
        if (isHttp) {
          nodes.push(
            <a
              key={keyIdx++}
              href={linkMatch[2]}
              target="_blank"
              rel="noreferrer"
              className="text-[#1A73E8] hover:underline"
            >
              {linkMatch[1]}
            </a>
          );
        } else {
          nodes.push(
            <span key={keyIdx++} className="text-[#1A73E8]">
              {linkMatch[1]}
            </span>
          );
        }
      } else {
        nodes.push(token);
      }
    } else if (token.startsWith('*') && token.endsWith('*')) {
      nodes.push(
        <em key={keyIdx++} className="italic">
          {token.slice(1, -1)}
        </em>
      );
    } else {
      nodes.push(token);
    }
    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function parseMarkdownBlocks(markdown: string): MarkdownBlock[] {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  const blocks: MarkdownBlock[] = [];
  let i = 0;

  const isTableSeparator = (line: string) =>
    /^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)+\|?\s*$/.test(line);

  const splitTableRow = (line: string) =>
    line
      .trim()
      .replace(/^\|/, '')
      .replace(/\|$/, '')
      .split('|')
      .map((cell) => cell.trim());

  while (i < lines.length) {
    const rawLine = lines[i];
    const trimmed = rawLine.trim();

    if (!trimmed) {
      i++;
      continue;
    }

    // Horizontal rule
    if (/^(-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      blocks.push({ type: 'hr' });
      i++;
      continue;
    }

    // Fenced code block
    const fenceMatch = trimmed.match(/^```([a-zA-Z0-9_-]*)/);
    if (fenceMatch) {
      const lang = fenceMatch[1] || 'text';
      i++;
      const codeLines: string[] = [];
      while (i < lines.length && !lines[i].trim().startsWith('```')) {
        codeLines.push(lines[i]);
        i++;
      }
      if (i < lines.length) i++;
      blocks.push({ type: 'code', lang, code: codeLines.join('\n') });
      continue;
    }

    // Heading (# .. ####)
    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        type: 'heading',
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      });
      i++;
      continue;
    }

    // Blockquote or GitHub Callout (> [!IMPORTANT], > [!CAUTION], ...)
    if (trimmed.startsWith('>')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('>')) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ''));
        i++;
      }
      const firstLine = quoteLines[0]?.trim() || '';
      const calloutMatch = firstLine.match(/^\[!(IMPORTANT|CAUTION|WARNING|NOTE|TIP)\]$/i);
      if (calloutMatch) {
        const kind = calloutMatch[1].toUpperCase() as CalloutKind;
        const innerMd = quoteLines.slice(1).join('\n').trim();
        blocks.push({
          type: 'callout',
          kind,
          blocks: parseMarkdownBlocks(innerMd),
        });
      } else {
        blocks.push({
          type: 'blockquote',
          blocks: parseMarkdownBlocks(quoteLines.join('\n')),
        });
      }
      continue;
    }

    // Markdown Table
    if (trimmed.includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = splitTableRow(rawLine);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().includes('|') && lines[i].trim() !== '') {
        rows.push(splitTableRow(lines[i]));
        i++;
      }
      blocks.push({ type: 'table', headers, rows });
      continue;
    }

    // Unordered or Ordered List
    const ulMatch = rawLine.match(/^\s*[-*+]\s+(.*)$/);
    const olMatch = rawLine.match(/^\s*\d+\.\s+(.*)$/);
    if (ulMatch || olMatch) {
      const ordered = Boolean(olMatch);
      const items: string[] = [];
      while (i < lines.length) {
        const cur = lines[i];
        const mUl = cur.match(/^\s*[-*+]\s+(.*)$/);
        const mOl = cur.match(/^\s*\d+\.\s+(.*)$/);
        if ((!ordered && mUl) || (ordered && mOl)) {
          const itemParts = [(ordered ? mOl![1] : mUl![1]).trim()];
          i++;
          // Absorb wrapped continuation lines belonging to this list item
          while (
            i < lines.length &&
            lines[i].trim() !== '' &&
            !/^\s*([-*+]|\d+\.)\s+/.test(lines[i]) &&
            !/^\s*(#{1,4}\s+|```|>)/.test(lines[i])
          ) {
            itemParts.push(lines[i].trim());
            i++;
          }
          items.push(itemParts.join(' '));
        } else if (cur.trim() === '') {
          // Allow single blank line between list items if next line continues same list type
          const next = lines[i + 1] || '';
          const nextContinues = ordered
            ? /^\s*\d+\.\s+/.test(next)
            : /^\s*[-*+]\s+/.test(next);
          if (nextContinues) {
            i++;
          } else {
            break;
          }
        } else {
          break;
        }
      }
      blocks.push({ type: 'list', ordered, items });
      continue;
    }

    // Paragraph (join consecutive wrapped lines)
    const paraLines: string[] = [trimmed];
    i++;
    while (
      i < lines.length &&
      lines[i].trim() !== '' &&
      !/^\s*(#{1,4}\s+|```|>|[-*+]\s+|\d+\.\s+)/.test(lines[i]) &&
      !(lines[i].includes('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
    ) {
      paraLines.push(lines[i].trim());
      i++;
    }
    blocks.push({ type: 'paragraph', text: paraLines.join(' ') });
  }

  return blocks;
}

const CALLOUT_STYLES: Record<CalloutKind, { bg: string; labelColor: string }> = {
  IMPORTANT: { bg: 'bg-[#F4F0FF]', labelColor: 'text-[#7C3AED]' },
  CAUTION: { bg: 'bg-[#FEF2F2]', labelColor: 'text-[#DC2626]' },
  WARNING: { bg: 'bg-[#FFF8EB]', labelColor: 'text-[#B45309]' },
  NOTE: { bg: 'bg-[#EFF6FF]', labelColor: 'text-[#1D4ED8]' },
  TIP: { bg: 'bg-[#ECFDF5]', labelColor: 'text-[#047857]' },
};

const MarkdownBlocksRenderer: React.FC<{ blocks: MarkdownBlock[]; compact?: boolean }> = ({
  blocks,
  compact = false,
}) => (
  <div className={compact ? 'space-y-2' : 'space-y-3'}>
    {blocks.map((block, idx) => {
      switch (block.type) {
        case 'heading': {
          if (block.level === 1) {
            return (
              <h2
                key={idx}
                className="text-[19px] font-semibold text-[#1F1F1F] tracking-[-0.01em] pt-2 first:pt-0"
              >
                {parseInlineMarkdown(block.text)}
              </h2>
            );
          }
          if (block.level === 2) {
            return (
              <h3
                key={idx}
                className="text-[15.5px] font-semibold text-[#1F1F1F] tracking-[-0.01em] pt-3 first:pt-0"
              >
                {parseInlineMarkdown(block.text)}
              </h3>
            );
          }
          return (
            <h4 key={idx} className="text-[14px] font-semibold text-[#1F1F1F] pt-2 first:pt-0">
              {parseInlineMarkdown(block.text)}
            </h4>
          );
        }
        case 'paragraph':
          return (
            <p key={idx} className="text-[13.5px] leading-[1.64] text-[#1F1F1F]">
              {parseInlineMarkdown(block.text)}
            </p>
          );
        case 'code':
          return (
            <div key={idx} className="rounded-xl bg-[#F5F6F8] px-4 py-3 overflow-x-auto">
              <pre className="font-mono text-[12px] leading-[1.55] text-[#1F1F1F]">
                <code>{block.code}</code>
              </pre>
            </div>
          );
        case 'list': {
          const ListTag = block.ordered ? 'ol' : 'ul';
          return (
            <ListTag
              key={idx}
              className={`${
                block.ordered ? 'list-decimal' : 'list-disc'
              } pl-5 space-y-1.5 text-[13.5px] leading-[1.6] text-[#1F1F1F]`}
            >
              {block.items.map((item, itemIdx) => (
                <li key={itemIdx}>{parseInlineMarkdown(item)}</li>
              ))}
            </ListTag>
          );
        }
        case 'callout': {
          const style = CALLOUT_STYLES[block.kind];
          return (
            <div key={idx} className={`rounded-xl ${style.bg} px-4 py-3.5 space-y-1.5`}>
              <div className={`text-[11.5px] font-semibold uppercase tracking-wide ${style.labelColor}`}>
                {block.kind}
              </div>
              <MarkdownBlocksRenderer blocks={block.blocks} compact />
            </div>
          );
        }
        case 'blockquote':
          return (
            <div key={idx} className="rounded-xl bg-[#F6F7F9] px-4 py-3">
              <MarkdownBlocksRenderer blocks={block.blocks} compact />
            </div>
          );
        case 'table':
          return (
            <div key={idx} className="overflow-x-auto rounded-xl bg-[#FAFBFD]">
              <table className="w-full text-left text-[12.5px] border-collapse">
                <thead>
                  <tr className="bg-[#F1F3F6] text-[#3C4043]">
                    {block.headers.map((header, hIdx) => (
                      <th key={hIdx} className="px-3 py-2 font-semibold">
                        {parseInlineMarkdown(header)}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#ECEEF2] text-[#1F1F1F]">
                  {block.rows.map((row, rIdx) => (
                    <tr key={rIdx}>
                      {row.map((cell, cIdx) => (
                        <td key={cIdx} className="px-3 py-2 align-top">
                          {parseInlineMarkdown(cell)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        case 'hr':
          return <hr key={idx} className="border-0 border-t border-[#ECEEF2] my-3" />;
        default:
          return null;
      }
    })}
  </div>
);

export const SkillDetailModal: React.FC<SkillDetailModalProps> = ({ skill, onClose }) => {
  const [copiedPath, setCopiedPath] = useState(false);

  useEffect(() => {
    if (!skill) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [skill, onClose]);

  useEffect(() => {
    setCopiedPath(false);
  }, [skill?.id]);

  if (!skill) return null;

  const parsedBlocks = parseMarkdownBlocks(skill.markdown);

  const handleCopyPath = () => {
    navigator.clipboard?.writeText(skill.filePath);
    setCopiedPath(true);
    setTimeout(() => setCopiedPath(false), 1500);
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/25 flex items-center justify-center p-6"
      role="dialog"
      aria-modal="true"
      aria-label={`/${skill.name}`}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-[780px] max-h-[85vh] bg-white rounded-[20px] shadow-[0_24px_64px_rgba(15,23,42,0.22)] flex flex-col overflow-hidden animate-fade-slide-up select-text"
      >
        {/* Top Modal Header */}
        <div className="flex items-center justify-between px-7 pt-6 pb-2 shrink-0">
          <h2 className="text-[16px] font-semibold text-[#1F1F1F] tracking-[-0.01em]">
            /{skill.name}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-[#F1F3F5] text-[#5F6368] hover:text-[#1F1F1F] flex items-center justify-center transition-colors cursor-pointer"
            title="Close"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable SKILL.md Content */}
        <div className="px-7 pb-8 overflow-y-auto">
          {/* File Path + Copy Button */}
          <div className="flex items-center gap-2 mt-1 mb-3">
            <span className="font-mono text-[12.5px] text-[#5F6368] break-all">
              {skill.filePath}
            </span>
            <button
              type="button"
              onClick={handleCopyPath}
              className="p-1 rounded-md text-[#5F6368] hover:text-[#1F1F1F] hover:bg-[#F1F3F5] transition-colors shrink-0 cursor-pointer"
              title="Copy SKILL.md path"
            >
              {copiedPath ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
            </button>
          </div>

          {/* Frontmatter Description */}
          <p className="text-[13.5px] leading-[1.6] text-[#5F6368]">{skill.description}</p>

          {/* Structural Neutral Divider */}
          <hr className="border-0 border-t border-[#ECEEF2] my-5" />

          {/* Rendered SKILL.md Markdown */}
          <MarkdownBlocksRenderer blocks={parsedBlocks} />
        </div>
      </div>
    </div>
  );
};
