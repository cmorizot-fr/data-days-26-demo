import React, { useEffect, useRef, useState } from 'react';
import {
  Folder,
  GitBranch,
  ChevronDown,
  ChevronUp,
  ChevronRight,
  Plus,
  ShieldAlert,
  Mic,
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  CornerDownLeft,
  Sparkles,
  Copy,
  ThumbsUp,
  ThumbsDown,
  FileDiff,
  ExternalLink,
  Check,
  Film,
  FileText,
  X,
} from 'lucide-react';
import { AntigravityArchLogo } from './Icons';
import { DEMO_SETTINGS } from '../data/scenarios';
import {
  AskQuestionItem,
  DemoScenario,
  ExecutionStepTrace,
  FileIconKind,
  InlineChip,
  InlineCodeBlock,
  PromptTurn,
  VisualCheckDocPreview,
  VisualTone,
} from '../types';
import { InspectorModalState } from './OverviewPanel';
import { PubSubInspectorCard } from './PubSubInspectorCard';
import { VisualCheckCard } from './VisualCheckCard';

const AVAILABLE_MODELS = DEMO_SETTINGS.availableModels;

export interface ExecutedTurn {
  turn: PromptTurn;
  userPromptText: string;
  status: 'thinking' | 'streaming' | 'done';
  visibleTraceCount: number;
}

const WorkingIndicator: React.FC = () => (
  <span className="inline-flex items-center gap-1.5 text-[14px] text-[#5F6368]">
    <span>Working</span>
    <span className="inline-flex items-center gap-[3.5px] translate-y-[1px]" aria-hidden="true">
      <span className="w-[4.5px] h-[4.5px] rounded-full bg-[#5F6368] animate-working-dot-1" />
      <span className="w-[4.5px] h-[4.5px] rounded-full bg-[#5F6368] animate-working-dot-2" />
    </span>
  </span>
);

const TurnCodeBlockCard: React.FC<{ block: InlineCodeBlock }> = ({ block }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText(block.code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className="mt-4 rounded-2xl bg-[#F6F7F9] p-4 space-y-3 select-text">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 min-w-0">
          <span className="px-2 py-0.5 rounded-md bg-[#E8EEF7] text-[#1D4ED8] font-mono text-[10.5px] font-bold uppercase shrink-0">
            {block.language}
          </span>
          <span className="font-mono text-[12.5px] font-medium text-[#111318] truncate">
            {block.label}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {block.actionLink && (
            <a
              href={block.actionLink.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg bg-white text-[12px] font-medium text-[#1A73E8] hover:bg-[#EFF6FF] transition-colors"
            >
              <span>{block.actionLink.label}</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          )}
          <button
            type="button"
            onClick={handleCopy}
            className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-white hover:bg-[#ECEEF2] text-[12px] font-medium text-[#202124] transition-colors cursor-pointer"
          >
            {copied ? <Check className="w-3.5 h-3.5 text-[#188038]" /> : <Copy className="w-3.5 h-3.5 text-[#5F6368]" />}
            <span>{copied ? 'Copié' : 'Copier SQL'}</span>
          </button>
        </div>
      </div>

      <pre className="rounded-xl bg-white p-3.5 font-mono text-[12px] leading-[1.55] text-[#111318] overflow-x-auto shadow-[0_1px_2px_rgba(15,23,42,0.04)]">
        <code>{block.code}</code>
      </pre>

      {block.resultTable && block.resultTable.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[11.5px] font-medium text-[#5F6368] px-0.5">
            Résultat retourné en direct par BigQuery (`roles/bigquerydatapolicy.maskedReader`) :
          </div>
          <pre className="rounded-xl bg-[#111318] text-[#F1F3F5] p-3.5 font-mono text-[11.5px] leading-[1.5] overflow-x-auto">
            <code>{block.resultTable.join('\n')}</code>
          </pre>
        </div>
      )}
    </div>
  );
};

interface ChatStageProps {
  scenario: DemoScenario;
  executedTurns: ExecutedTurn[];
  dakInstalled: boolean;
  isStreaming: boolean;
  onSendTurn: (turn: PromptTurn, customText?: string) => void;
  onOpenCustomizations: () => void;
  onOpenVisualSkill: () => void;
  onOpenInspector: (modal: InspectorModalState) => void;
}

/**
 * Renders inline `**bold**` and backtick `` `code` `` segments cleanly.
 */
const renderCodeSegments = (segment: string, keyPrefix: string): React.ReactNode => {
  const parts = segment.split(/(`[^`]+`|\[[^\]]+\]\(https?:\/\/[^)]+\))/g);
  return parts.map((part, idx) => {
    if (part.startsWith('`') && part.endsWith('`')) {
      const code = part.slice(1, -1);
      return (
        <code
          key={`${keyPrefix}-c-${idx}`}
          className="px-1.5 py-[1px] mx-[1px] rounded-[5px] bg-[#F1F3F5] text-[#202124] font-mono text-[12.5px]"
        >
          {code}
        </code>
      );
    }
    const linkMatch = /^\[([^\]]+)\]\((https?:\/\/[^)]+)\)$/.exec(part);
    if (linkMatch) {
      return (
        <a
          key={`${keyPrefix}-a-${idx}`}
          href={linkMatch[2]}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-0.5 text-[#1A73E8] hover:underline font-medium"
        >
          <span>{linkMatch[1]}</span>
          <ExternalLink className="w-3 h-3 inline ml-0.5" />
        </a>
      );
    }
    return <span key={`${keyPrefix}-t-${idx}`}>{part}</span>;
  });
};

const renderAntigravityInlineText = (text: string): React.ReactNode => {
  const boldParts = text.split(/(\*\*[^*]+\*\*)/g);
  return boldParts.map((bPart, bIdx) => {
    if (bPart.startsWith('**') && bPart.endsWith('**')) {
      const inner = bPart.slice(2, -2);
      return (
        <strong key={`b-${bIdx}`} className="font-semibold text-[#111318]">
          {renderCodeSegments(inner, `b-${bIdx}`)}
        </strong>
      );
    }
    return <React.Fragment key={`n-${bIdx}`}>{renderCodeSegments(bPart, `n-${bIdx}`)}</React.Fragment>;
  });
};

const badgeSurfaceClass = (tone?: VisualTone): string => {
  switch (tone) {
    case 'positive':
      return 'bg-emerald-500/12 text-emerald-900';
    case 'warning':
      return 'bg-amber-500/14 text-amber-900';
    case 'ruby':
      return 'bg-rose-500/12 text-rose-900';
    case 'blue':
      return 'bg-[#E8F0FE] text-[#174EA6]';
    default:
      return 'bg-[#F1F3F5] text-[#3C4043]';
  }
};

/**
 * Mini file-type glyph used inside the pure-white "Analyzed / Edited" work tree (matching media_1794580203737.png)
 */
const WorkTreeFileGlyph: React.FC<{ kind: FileIconKind }> = ({ kind }) => {
  switch (kind) {
    case 'sql':
      return <span className="text-[10px] font-bold tracking-tight text-[#1A73E8]">SQL</span>;
    case 'yml':
      return <span className="text-[10px] font-bold tracking-tight text-[#D97706]">YML</span>;
    case 'py':
      return <span className="text-[10px] font-bold tracking-tight text-[#2563EB]">PY</span>;
    case 'dak':
      return <Sparkles className="w-3.5 h-3.5 text-[#1A73E8] inline" />;
    case 'cpy':
      return <span className="text-[10px] font-bold tracking-tight text-[#5F6368]">CPY</span>;
    case 'csv':
      return <span className="text-[10px] font-bold tracking-tight text-[#188038]">CSV</span>;
    case 'mp4':
      return <Film className="w-3.5 h-3.5 text-[#EA4335] inline" />;
    case 'md':
      return <FileText className="w-3.5 h-3.5 text-[#5F6368] inline" />;
  }
};

/**
 * Tokenizes a shell command line with Antigravity's terminal syntax colors:
 * - Command binary: coral red (#D93025)
 * - CLI flags (-rn, --project=...): warm amber (#D97706)
 * - Quoted strings ("...", '...'): forest green (#188038)
 * - Paths & arguments: crisp ink (#111318)
 */
const renderShellCommand = (cmd: string): React.ReactNode => {
  const tokenRegex = /([A-Z_][A-Z0-9_]*=(?:"[^"]*"|'[^']*'|[^\s]+)|"[^"]*"|'[^']*'|\s+|\|\||&&|[|;<>]|[^\s|;&<>]+)/g;
  const tokens = cmd.match(tokenRegex) ?? [cmd];
  let expectBinary = true;

  return tokens.map((tok, idx) => {
    if (/^\s+$/.test(tok)) {
      return <span key={idx}>{tok}</span>;
    }
    if (tok === '&&' || tok === '||' || tok === '|' || tok === ';') {
      expectBinary = true;
      return (
        <span key={idx} className="text-[#5F6368]">
          {tok}
        </span>
      );
    }
    if (tok === '<' || tok === '>') {
      return (
        <span key={idx} className="text-[#5F6368]">
          {tok}
        </span>
      );
    }
    // ENV_VAR="value" prefix before the binary
    const envMatch = tok.match(/^([A-Z_][A-Z0-9_]*=)(.*)$/);
    if (envMatch && expectBinary) {
      const [, prefix, val] = envMatch;
      const isQuoted =
        (val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"));
      return (
        <span key={idx}>
          <span className="text-[#5F6368]">{prefix}</span>
          <span className={isQuoted ? 'text-[#188038]' : 'text-[#111318]'}>{val}</span>
        </span>
      );
    }
    if (expectBinary) {
      expectBinary = false;
      return (
        <span key={idx} className="text-[#D93025]">
          {tok}
        </span>
      );
    }
    if ((tok.startsWith('"') && tok.endsWith('"')) || (tok.startsWith("'") && tok.endsWith("'"))) {
      return (
        <span key={idx} className="text-[#188038]">
          {tok}
        </span>
      );
    }
    if (tok.startsWith('-')) {
      const eqIdx = tok.indexOf('=');
      if (eqIdx > 0) {
        const flagPart = tok.slice(0, eqIdx + 1);
        const valPart = tok.slice(eqIdx + 1);
        return (
          <span key={idx}>
            <span className="text-[#D97706]">{flagPart}</span>
            <span className="text-[#111318]">{valPart}</span>
          </span>
        );
      }
      return (
        <span key={idx} className="text-[#D97706]">
          {tok}
        </span>
      );
    }
    return (
      <span key={idx} className="text-[#111318]">
        {tok}
      </span>
    );
  });
};

/**
 * Renders a single row in the "Worked for Xs -> Explored files, ran commands, edited files" tree
 * Clicking a "Ran ..." row expands its inline command & output card directly underneath!
 */
const WorkTreeStepRow: React.FC<{
  trace: ExecutionStepTrace;
  defaultCwd: string;
  fallbackLogs: string[];
  isActiveStep: boolean;
  isRanExpanded: boolean;
  onToggleRan: () => void;
  onClickFile: () => void;
}> = ({
  trace,
  defaultCwd,
  fallbackLogs,
  isActiveStep,
  isRanExpanded,
  onToggleRan,
  onClickFile,
}) => {
  const pulseClass = isActiveStep ? 'animate-pulse' : '';

  if (trace.action === 'ran') {
    const cwdLabel = trace.cwd || defaultCwd;
    let commandLine = trace.command || '';
    let outputLines = trace.output || [];

    if (!commandLine && fallbackLogs.length > 0) {
      const firstCmdIdx = fallbackLogs.findIndex((l) => l.startsWith('$ '));
      if (firstCmdIdx >= 0) {
        commandLine = fallbackLogs[firstCmdIdx].slice(2);
        const rest: string[] = [];
        for (let i = firstCmdIdx + 1; i < fallbackLogs.length; i++) {
          if (fallbackLogs[i].startsWith('$ ')) break;
          rest.push(fallbackLogs[i]);
        }
        outputLines = rest;
      }
    }
    if (!commandLine) {
      commandLine = trace.commandSummary;
    }

    return (
      <div className={`animate-fade-slide-up ${pulseClass}`}>
        <button
          type="button"
          onClick={onToggleRan}
          className="inline-flex items-center gap-1 text-[14px] text-[#5F6368] hover:text-[#202124] text-left transition-colors cursor-pointer"
        >
          <span>Ran {trace.commandSummary}</span>
          {isRanExpanded ? (
            <ChevronDown className="w-3.5 h-3.5 shrink-0 text-[#70757A]" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 shrink-0 text-[#70757A]" />
          )}
        </button>

        {isRanExpanded && (
          <div className="mt-2 mb-1 rounded-xl bg-white shadow-[0_1px_6px_rgba(15,23,42,0.07)] divide-y divide-[#F0F1F3] overflow-hidden animate-fade-slide-up">
            {/* Command Prompt Header */}
            <div className="px-3.5 py-2.5 font-mono text-[13px] leading-snug overflow-x-auto whitespace-nowrap select-text">
              <span className="text-[#6E7681]">~/.../{cwdLabel} $ </span>
              {renderShellCommand(commandLine)}
            </div>

            {/* Command Output Body with soft bottom fade when multi-line */}
            {outputLines.length > 0 && (
              <div className="relative">
                <div className="px-3.5 py-2.5 font-mono text-[13px] leading-[1.55] text-[#111318] max-h-[146px] overflow-y-auto select-text">
                  {outputLines.map((line, lIdx) => (
                    <div key={lIdx} className="whitespace-pre-wrap break-all">
                      {line}
                    </div>
                  ))}
                </div>
                {outputLines.length >= 5 && (
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 h-7 bg-gradient-to-t from-white via-white/80 to-transparent" />
                )}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  if (trace.action === 'analyzed') {
    return (
      <div
        className={`flex items-center gap-2 text-[14px] text-[#5F6368] animate-fade-slide-up ${pulseClass}`}
      >
        <span>Analyzed</span>
        <span className="inline-flex items-center gap-1.5 text-[#3C4043] font-medium">
          <WorkTreeFileGlyph kind={trace.icon} />
          <span>{trace.fileName}</span>
        </span>
        {trace.lineRange && <span className="text-[#5F6368]">{trace.lineRange}</span>}
      </div>
    );
  }

  // trace.action === 'edited'
  return (
    <div className={`animate-fade-slide-up ${pulseClass}`}>
      <button
        type="button"
        onClick={onClickFile}
        className="inline-flex items-center gap-2 text-[14px] text-[#5F6368] hover:text-[#202124] transition-colors cursor-pointer"
      >
        <span>Edited</span>
        <span className="inline-flex items-center gap-1.5 text-[#3C4043] font-medium">
          <WorkTreeFileGlyph kind={trace.icon} />
          <span>{trace.fileName}</span>
        </span>
        <span className="text-[13px] font-medium text-[#188038] ml-0.5">+{trace.added}</span>
        <span className="text-[13px] font-medium text-[#D93025]">-{trace.removed}</span>
      </button>
    </div>
  );
};

/**
 * Renders Antigravity inline file / symbol chip inside the final numbered summary
 */
const InlineFileChip: React.FC<{ chip: InlineChip; onClick: () => void }> = ({ chip, onClick }) => {
  const renderPrefix = () => {
    switch (chip.kind) {
      case 'sql':
        return <span className="text-[10px] font-bold tracking-tight text-[#1A73E8]">SQL</span>;
      case 'yml':
        return <span className="text-[10px] font-bold tracking-tight text-[#D97706]">YML</span>;
      case 'py':
        return <span className="text-[10px] font-bold tracking-tight text-[#2563EB]">PY</span>;
      case 'bq':
        return <span className="text-[10px] font-bold tracking-tight text-[#188038]">BQ</span>;
      case 'kc':
        return <span className="text-[10px] font-bold tracking-tight text-[#9333EA]">KC</span>;
      case 'mp4':
        return <Film className="w-3 h-3 text-[#EA4335]" />;
    }
  };

  return (
    <button
      type="button"
      onClick={onClick}
      className="inline-flex items-center gap-1.5 px-1.5 py-[1px] rounded-[6px] bg-[#F1F3F5] hover:bg-[#E5E8EC] text-[#202124] font-mono text-[12.5px] font-normal align-baseline transition-colors cursor-pointer"
    >
      {renderPrefix()}
      <span>{chip.label}</span>
    </button>
  );
};

const VoiceSparkleIcon: React.FC = () => (
  <svg viewBox="0 0 20 20" fill="none" className="w-4 h-4">
    <rect x="4.2" y="7" width="1.6" height="6" rx="0.8" fill="currentColor" />
    <rect x="7.6" y="4.5" width="1.6" height="11" rx="0.8" fill="currentColor" />
    <rect x="11" y="6.5" width="1.6" height="7" rx="0.8" fill="currentColor" />
    <path
      d="M15.3 3.2L15.9 4.9L17.6 5.5L15.9 6.1L15.3 7.8L14.7 6.1L13 5.5L14.7 4.9L15.3 3.2Z"
      fill="currentColor"
    />
  </svg>
);

/** The question tray shows plain text only: no bold, no inline code chips. */
const stripInlineMarkup = (text: string): string => text.replace(/\*\*/g, '').replace(/`/g, '');

const AskQuestionGlyph: React.FC = () => (
  <svg viewBox="0 0 20 20" fill="none" className="w-[19px] h-[19px] shrink-0 text-[#5F6368]">
    <circle cx="9.5" cy="10.5" r="7.4" stroke="currentColor" strokeWidth="1.35" />
    <path
      d="M7.5 8.7a2.05 2.05 0 1 1 3.1 1.75c-.65.4-1.05.85-1.05 1.6"
      stroke="currentColor"
      strokeWidth="1.35"
      strokeLinecap="round"
    />
    <circle cx="9.55" cy="14.1" r="0.8" fill="currentColor" />
    <circle cx="16.1" cy="3.9" r="3.3" fill="#FFFFFF" />
    <circle cx="16.1" cy="3.9" r="2.1" fill="#1A73E8" />
  </svg>
);

/**
 * Interactive Antigravity `ask_question` Tray docked directly above the composer.
 * Strictly zero colored borders or rings — hierarchy uses pure surface luminance & typography.
 */
const AskQuestionTray: React.FC<{
  questions: AskQuestionItem[];
  currentIdx: number;
  selectedChoices: Record<string, number>;
  otherTexts: Record<string, string>;
  collapsed: boolean;
  onChangeIdx: (idx: number) => void;
  onSelectChoice: (qId: string, optionIdx: number) => void;
  onChangeOtherText: (qId: string, text: string) => void;
  onToggleCollapse: () => void;
  onDismiss: () => void;
  onSkip: () => void;
  onContinue: () => void;
}> = ({
  questions,
  currentIdx,
  selectedChoices,
  otherTexts,
  collapsed,
  onChangeIdx,
  onSelectChoice,
  onChangeOtherText,
  onToggleCollapse,
  onDismiss,
  onSkip,
  onContinue,
}) => {
  const safeIdx = Math.min(Math.max(0, currentIdx), questions.length - 1);
  const q = questions[safeIdx];
  const otherOptionIdx = q.options.length;
  const chosenIdx = selectedChoices[q.id] ?? 0;
  const otherVal = otherTexts[q.id] ?? '';
  // Rows stay visually neutral (as in the original) until the speaker explicitly picks one.
  const hasExplicitChoice = selectedChoices[q.id] !== undefined;

  return (
    <div className="mb-2.5 rounded-[22px] bg-white px-4 pt-3.5 pb-2.5 shadow-[0_1px_3px_rgba(15,23,42,0.07),0_6px_20px_rgba(15,23,42,0.05)] animate-fade-slide-up select-none">
      {/* Header Row: Question Icon + Question Title + Pagination / Collapse / Close */}
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="mt-[1px]">
            <AskQuestionGlyph />
          </div>
          <div className="text-[15px] font-medium text-[#111318] leading-snug">
            {stripInlineMarkup(q.question)}
          </div>
        </div>

        <div className="flex items-center gap-1.5 text-[#5F6368] shrink-0 pt-0.5">
          {questions.length > 1 && (
            <div className="inline-flex items-center gap-1.5 mr-1">
              <button
                type="button"
                disabled={safeIdx === 0}
                onClick={() => onChangeIdx(safeIdx - 1)}
                className="w-6 h-6 rounded-full hover:bg-[#F1F3F5] disabled:opacity-30 flex items-center justify-center transition-colors cursor-pointer disabled:cursor-default"
                title="Question précédente"
              >
                <ArrowLeft className="w-3.5 h-3.5" />
              </button>
              <span className="text-[14px] font-normal text-[#3C4043] tabular-nums">
                {safeIdx + 1}/{questions.length}
              </span>
              <button
                type="button"
                disabled={safeIdx === questions.length - 1}
                onClick={() => onChangeIdx(safeIdx + 1)}
                className="w-6 h-6 rounded-full hover:bg-[#F1F3F5] disabled:opacity-30 flex items-center justify-center transition-colors cursor-pointer disabled:cursor-default"
                title="Question suivante"
              >
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          <button
            type="button"
            onClick={onToggleCollapse}
            className="w-6 h-6 rounded-full hover:bg-[#F1F3F5] flex items-center justify-center transition-colors cursor-pointer"
            title={collapsed ? 'Déplier' : 'Replier'}
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform ${collapsed ? 'rotate-180' : ''}`}
            />
          </button>

          <button
            type="button"
            onClick={onDismiss}
            className="w-6 h-6 rounded-full hover:bg-[#F1F3F5] flex items-center justify-center transition-colors cursor-pointer"
            title="Fermer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Options Body */}
      {!collapsed && (
        <div className="mt-2.5 -mx-1.5">
          {q.options.map((optText, oIdx) => {
            const isSelected = hasExplicitChoice && chosenIdx === oIdx;
            return (
              <button
                key={oIdx}
                type="button"
                onClick={() => onSelectChoice(q.id, oIdx)}
                className={`w-full flex items-center gap-3 px-1.5 py-[7px] rounded-lg text-left transition-colors cursor-pointer ${
                  isSelected ? 'bg-[#F1F3F5]' : 'hover:bg-[#F6F7F9]'
                }`}
              >
                <span className="w-[19px] h-[19px] rounded-[5px] bg-[#F1F3F5] text-[12px] font-medium text-[#3C4043] flex items-center justify-center shrink-0">
                  {oIdx + 1}
                </span>
                <span className="text-[15px] font-normal text-[#3C4043] leading-snug">
                  {stripInlineMarkup(optText)}
                </span>
              </button>
            );
          })}

          {/* Bottom Row: Option N+1 "Other (write your answer)" + Mic / Skip / Continue ↵ */}
          <div
            onClick={() => onSelectChoice(q.id, otherOptionIdx)}
            className="flex items-center justify-between gap-3 px-1.5 py-[3px] rounded-lg"
          >
            <div className="flex items-center gap-3 flex-1 min-w-0">
              <span className="w-[19px] h-[19px] rounded-[5px] bg-[#F1F3F5] text-[12px] font-medium text-[#3C4043] flex items-center justify-center shrink-0">
                {otherOptionIdx + 1}
              </span>
              <input
                type="text"
                value={otherVal}
                onFocus={() => onSelectChoice(q.id, otherOptionIdx)}
                onChange={(e) => {
                  onSelectChoice(q.id, otherOptionIdx);
                  onChangeOtherText(q.id, e.target.value);
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onContinue();
                  }
                }}
                placeholder="Other (write your answer)"
                className="w-full bg-transparent text-[15px] font-normal text-[#3C4043] placeholder:text-[#80868B] focus:outline-none"
              />
            </div>

            <div
              onClick={(e) => e.stopPropagation()}
              className="flex items-center gap-3 shrink-0"
            >
              <button
                type="button"
                className="w-7 h-7 rounded-full hover:bg-[#F1F3F5] flex items-center justify-center text-[#3C4043] cursor-pointer"
                title="Dictée vocale"
              >
                <Mic className="w-4 h-4" strokeWidth={1.75} />
              </button>

              <button
                type="button"
                onClick={onSkip}
                className="px-2 py-1 rounded-lg hover:bg-[#F1F3F5] text-[15px] font-normal text-[#5F6368] transition-colors cursor-pointer"
              >
                Skip
              </button>

              <button
                type="button"
                onClick={onContinue}
                className="inline-flex items-center gap-2 pl-3.5 pr-3 py-[5px] rounded-full bg-[#A3C1EE] hover:bg-[#8FB3EA] text-white text-[15px] font-medium transition-colors cursor-pointer"
              >
                <span>Continue</span>
                <CornerDownLeft className="w-3.5 h-3.5" strokeWidth={2} />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export const ChatStage: React.FC<ChatStageProps> = ({
  scenario,
  executedTurns,
  dakInstalled,
  isStreaming,
  onSendTurn,
  onOpenCustomizations,
  onOpenVisualSkill,
  onOpenInspector,
}) => {
  const [inputValue, setInputValue] = useState('');
  const [selectedTurnIndex, setSelectedTurnIndex] = useState<number | null>(null);
  const [expandedTraces, setExpandedTraces] = useState<Record<string, boolean>>({});
  const [expandedSubGroups, setExpandedSubGroups] = useState<Record<string, boolean>>({});
  const [expandedRanSteps, setExpandedRanSteps] = useState<Record<string, boolean>>({});
  const [selectedModel, setSelectedModel] = useState<string>(AVAILABLE_MODELS[0]);
  const [modelMenuOpen, setModelMenuOpen] = useState<boolean>(false);
  const [slashMenuOpen, setSlashMenuOpen] = useState<boolean>(false);
  const [previewDoc, setPreviewDoc] = useState<VisualCheckDocPreview | null>(null);

  // Interactive `ask_question` tray state (keyed per completed turn)
  const [questionStepIdx, setQuestionStepIdx] = useState<number>(0);
  const [questionChoices, setQuestionChoices] = useState<Record<string, number>>({});
  const [questionOtherTexts, setQuestionOtherTexts] = useState<Record<string, string>>({});
  const [questionCollapsed, setQuestionCollapsed] = useState<boolean>(false);
  const [dismissedQuestionTurnId, setDismissedQuestionTurnId] = useState<string | null>(null);

  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const scrollEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const typingTimerRef = useRef<number | null>(null);
  const typingTargetRef = useRef<string | null>(null);

  const stopTypewriter = () => {
    if (typingTimerRef.current !== null) {
      window.clearTimeout(typingTimerRef.current);
      typingTimerRef.current = null;
    }
    typingTargetRef.current = null;
  };

  const startTypewriterPrompt = (fullText: string) => {
    stopTypewriter();
    typingTargetRef.current = fullText;
    setInputValue('');
    textareaRef.current?.focus();

    // Calibrate speed so ~100 chars takes ~2.2s and ~200 chars takes ~3.2s with human cadence
    const baseMs = fullText.length > 150 ? 12 : 18;
    let cursor = 0;

    const typeNext = () => {
      cursor += 1;
      const nextSlice = fullText.slice(0, cursor);
      setInputValue(nextSlice);

      if (textareaRef.current) {
        textareaRef.current.selectionStart = cursor;
        textareaRef.current.selectionEnd = cursor;
      }

      if (cursor >= fullText.length) {
        typingTimerRef.current = null;
        typingTargetRef.current = null;
        return;
      }

      const ch = fullText[cursor - 1];
      const pausePunct = /[.,:;!?]/.test(ch) ? 45 : ch === ' ' ? 8 : 0;
      const jitter = Math.floor(Math.random() * 14);
      typingTimerRef.current = window.setTimeout(typeNext, baseMs + jitter + pausePunct);
    };

    typingTimerRef.current = window.setTimeout(typeNext, 40);
  };

  useEffect(() => {
    return () => stopTypewriter();
  }, []);

  const completedIds = new Set(executedTurns.map((et) => et.turn.id));
  const nextSuggestedTurn = scenario.turns.find((t) => !completedIds.has(t.id)) || null;
  const lastExecutedItem =
    executedTurns.length > 0 ? executedTurns[executedTurns.length - 1] : null;
  const activeAskTurn =
    !isStreaming &&
    lastExecutedItem?.status === 'done' &&
    lastExecutedItem.turn.askQuestions &&
    lastExecutedItem.turn.askQuestions.length > 0 &&
    nextSuggestedTurn &&
    dismissedQuestionTurnId !== lastExecutedItem.turn.id
      ? lastExecutedItem.turn
      : null;

  useEffect(() => {
    stopTypewriter();
    setInputValue('');
    setSelectedTurnIndex(null);
    setSlashMenuOpen(false);
    setExpandedRanSteps({});
    setQuestionStepIdx(0);
    setQuestionChoices({});
    setQuestionOtherTexts({});
    setQuestionCollapsed(false);
    setDismissedQuestionTurnId(null);
  }, [scenario.id]);

  useEffect(() => {
    setQuestionStepIdx(0);
    setQuestionCollapsed(false);
  }, [lastExecutedItem?.turn.id]);

  useEffect(() => {
    scrollEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [executedTurns, activeAskTurn?.id]);

  const handleSelectChip = (turn: PromptTurn, idx: number) => {
    if (isStreaming) return;
    setSelectedTurnIndex(idx);
    setSlashMenuOpen(false);
    startTypewriterPrompt(turn.prompt);
  };

  const handleContinueQuestion = () => {
    if (!activeAskTurn || !activeAskTurn.askQuestions || !nextSuggestedTurn) return;
    const questions = activeAskTurn.askQuestions;
    if (questionStepIdx < questions.length - 1) {
      setQuestionStepIdx((prev) => prev + 1);
      return;
    }

    // All questions answered -> check if user customized any option vs default index 0
    const hasCustomAnswer = questions.some((q) => {
      const idx = questionChoices[q.id] ?? 0;
      if (idx === q.options.length) {
        return Boolean((questionOtherTexts[q.id] ?? '').trim());
      }
      return idx !== 0;
    });

    let finalPrompt = nextSuggestedTurn.prompt;
    if (hasCustomAnswer) {
      const chosenLines = questions.map((q, i) => {
        const idx = questionChoices[q.id] ?? 0;
        if (idx === q.options.length) {
          const custom = (questionOtherTexts[q.id] ?? '').trim();
          return `${i + 1}. ${custom || q.options[0].replace(/^\(Recommended\)\s*/i, '')}`;
        }
        return `${i + 1}. ${q.options[idx].replace(/^\(Recommended\)\s*/i, '')}`;
      });
      finalPrompt = chosenLines.join(' · ');
    }

    setDismissedQuestionTurnId(activeAskTurn.id);
    onSendTurn(nextSuggestedTurn, finalPrompt);
  };

  const handleSkipQuestion = () => {
    if (!activeAskTurn || !activeAskTurn.askQuestions) return;
    if (questionStepIdx < activeAskTurn.askQuestions.length - 1) {
      setQuestionStepIdx((prev) => prev + 1);
    } else {
      setDismissedQuestionTurnId(activeAskTurn.id);
    }
  };

  const handleSubmit = () => {
    if (isStreaming) return;
    const fullPending = typingTargetRef.current;
    stopTypewriter();

    const trimmed = (fullPending ?? inputValue).trim();
    if (!trimmed && !nextSuggestedTurn) return;

    const turnToRun =
      (selectedTurnIndex !== null && scenario.turns[selectedTurnIndex]) ||
      nextSuggestedTurn ||
      scenario.turns[scenario.turns.length - 1];

    onSendTurn(turnToRun, trimmed || turnToRun.prompt);
    setInputValue('');
    setSelectedTurnIndex(null);
    setSlashMenuOpen(false);
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    stopTypewriter();
    const val = e.target.value;
    setInputValue(val);
    if (val === '/') {
      setSlashMenuOpen(true);
    } else if (slashMenuOpen && !val.startsWith('/')) {
      setSlashMenuOpen(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Tab' && !inputValue.trim() && nextSuggestedTurn) {
      e.preventDefault();
      startTypewriterPrompt(nextSuggestedTurn.prompt);
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const toggleTrace = (id: string) => {
    setExpandedTraces((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleSubGroup = (id: string) => {
    setExpandedSubGroups((prev) => ({ ...prev, [id]: !(prev[id] ?? true) }));
  };

  const isEmpty = executedTurns.length === 0;

  return (
    <div className="flex-1 flex flex-col h-full min-w-0 relative bg-white">
      {/* Main Scrollable Discussion Area */}
      <div
        ref={scrollContainerRef}
        className={`flex-1 overflow-y-auto px-8 ${activeAskTurn ? 'pb-96' : 'pb-48'}`}
      >
        {isEmpty ? (
          /* Empty Welcome State matching Screenshot 1 */
          <div className="h-full min-h-[420px] flex flex-col items-center justify-center text-center select-none">
            <AntigravityArchLogo className="w-24 h-20 mb-5" />
            <h1 className="text-[24px] font-medium tracking-tight text-[#111318]">
              Hey {scenario.greetingName}, what should we build today?
            </h1>

            {!dakInstalled && (
              <div className="mt-4">
                <button
                  onClick={onOpenCustomizations}
                  className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#F3F4F7] hover:bg-[#E8EAEE] text-[12.5px] text-[#4B5563] font-medium transition-colors cursor-pointer"
                >
                  <Sparkles className="w-3.5 h-3.5 text-[#5F6368]" />
                  <span>Découvrir le plugin Data Agent Kit dans Customizations →</span>
                </button>
              </div>
            )}
          </div>
        ) : (
          /* Active Conversation Stream matching media_1794580203737.png + media_1794577724122.png */
          <div className="max-w-[760px] mx-auto pt-8 space-y-10">
            {executedTurns.map((item) => {
              const { turn, userPromptText, status, visibleTraceCount } = item;
              // Open while working so audience sees every Analyzed/Ran/Edited step live;
              // collapses cleanly once done (and re-opens on click!)
              const isTraceOpen = expandedTraces[turn.id] ?? status === 'streaming';
              const isSubGroupOpen = expandedSubGroups[turn.id] ?? true;

              const totalAdded = turn.filesChanged.reduce((acc, f) => acc + f.added, 0);
              const totalRemoved = turn.filesChanged.reduce((acc, f) => acc + f.removed, 0);

              return (
                <div key={turn.id} className="space-y-6 animate-fade-slide-up">
                  {/* 1. User Message Pill Bubble on the right */}
                  <div className="flex justify-end">
                    <div className="max-w-[78%] rounded-[24px] bg-white px-5 py-3 text-[14.5px] text-[#111318] leading-relaxed shadow-[0_2px_14px_rgba(0,0,0,0.06)] space-y-2.5">
                      {turn.promptAttachment && (
                        <button
                          type="button"
                          onClick={() => setPreviewDoc(turn.promptAttachment!)}
                          title="Cliquer pour agrandir le document joint"
                          className="w-full text-left rounded-2xl bg-[#F4F6F9] hover:bg-[#ECEFF4] p-2.5 transition-colors cursor-pointer space-y-2"
                        >
                          <div className="overflow-hidden rounded-xl bg-white">
                            <img
                              src={turn.promptAttachment.imageUrl}
                              alt={turn.promptAttachment.title}
                              className="w-full max-h-44 object-contain"
                            />
                          </div>
                          <div className="flex items-center justify-between gap-2 px-1">
                            <div className="min-w-0">
                              <div className="text-[12.5px] font-medium text-[#111318] truncate">
                                {turn.promptAttachment.title}
                              </div>
                              <div className="text-[11px] text-[#5F6368] truncate">
                                {turn.promptAttachment.subtitle}
                              </div>
                            </div>
                            <span className="px-2 py-0.5 rounded-md bg-white text-[#3C4043] font-mono text-[10.5px] font-medium shrink-0">
                              {turn.promptAttachment.metaBadge}
                            </span>
                          </div>
                        </button>
                      )}
                      <div>{userPromptText}</div>
                    </div>
                  </div>

                  {/* 2. Antigravity Editorial Turn Stream */}
                  <div className="space-y-4 text-[14.5px] text-[#202124] leading-[1.65]">
                    {status === 'thinking' ? (
                      <div className="py-1 animate-fade-slide-up">
                        <WorkingIndicator />
                      </div>
                    ) : (
                      <>
                        {/* Two-level pure-white Work Tree matching media_1794580203737.png */}
                        <div>
                          <button
                            type="button"
                            onClick={() => toggleTrace(turn.id)}
                            className="inline-flex items-center gap-1 text-[14px] text-[#5F6368] hover:text-[#202124] transition-colors cursor-pointer"
                          >
                            {status === 'streaming' ? (
                              <WorkingIndicator />
                            ) : (
                              <span>{turn.workedDurationLabel}</span>
                            )}
                            {isTraceOpen ? (
                              <ChevronDown className="w-3.5 h-3.5 text-[#70757A]" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-[#70757A]" />
                            )}
                          </button>

                          {isTraceOpen && (
                            <div className="mt-2.5 pl-3.5 space-y-2.5">
                              {/* Level 1: "Explored files, ran commands, edited files ⌄" */}
                              <button
                                type="button"
                                onClick={() => toggleSubGroup(turn.id)}
                                className="inline-flex items-center gap-1 text-[14px] text-[#5F6368] hover:text-[#202124] transition-colors cursor-pointer"
                              >
                                <span>{turn.workGroupSummary}</span>
                                {isSubGroupOpen ? (
                                  <ChevronDown className="w-3.5 h-3.5 text-[#70757A]" />
                                ) : (
                                  <ChevronRight className="w-3.5 h-3.5 text-[#70757A]" />
                                )}
                              </button>

                              {/* Level 2: Indented Ran / Analyzed / Edited lines directly on white canvas */}
                              {isSubGroupOpen && (
                                <div className="pl-4 space-y-2.5">
                                  {turn.traces.slice(0, visibleTraceCount).map((tr, idx) => (
                                    <WorkTreeStepRow
                                      key={tr.id}
                                      trace={tr}
                                      defaultCwd={scenario.projectFolder}
                                      fallbackLogs={turn.terminalLogs}
                                      isActiveStep={
                                        status === 'streaming' && idx === visibleTraceCount - 1
                                      }
                                      isRanExpanded={Boolean(expandedRanSteps[tr.id])}
                                      onToggleRan={() =>
                                        setExpandedRanSteps((prev) => ({
                                          ...prev,
                                          [tr.id]: !prev[tr.id],
                                        }))
                                      }
                                      onClickFile={() =>
                                        turn.filesChanged.length > 0 &&
                                        onOpenInspector({
                                          kind: 'review',
                                          files: turn.filesChanged,
                                        })
                                      }
                                    />
                                  ))}
                                </div>
                              )}
                            </div>
                          )}
                        </div>

                        {/* Intermediate status sentence once at least half the steps ran or done */}
                        {(status === 'done' ||
                          (status === 'streaming' &&
                            visibleTraceCount >= Math.ceil(turn.traces.length / 2))) && (
                          <p className="text-[#202124] animate-fade-slide-up">
                            {renderAntigravityInlineText(turn.intermediateMessage)}
                          </p>
                        )}
                      </>
                    )}

                    {/* Final completed blocks */}
                    {status === 'done' && (
                      <div className="space-y-4 animate-fade-slide-up">
                        {/* Task finished grey chevron line */}
                        <div>
                          <button
                            type="button"
                            onClick={() =>
                              turn.terminalLogs.length > 0 &&
                              onOpenInspector({ kind: 'terminal', logs: turn.terminalLogs })
                            }
                            className="inline-flex items-center gap-1 text-[14px] text-[#5F6368] hover:text-[#202124] transition-colors cursor-pointer"
                          >
                            <span>{turn.taskFinishedLabel}</span>
                            <ChevronRight className="w-4 h-4" />
                          </button>
                        </div>

                        {/* Lead confirmation paragraph + external blue link */}
                        <p className="text-[#202124]">
                          {renderAntigravityInlineText(turn.leadConfirmation)}
                          {turn.leadLink && (
                            <>
                              {' '}
                              <a
                                href={turn.leadLink.url}
                                target="_blank"
                                rel="noreferrer"
                                className="inline-flex items-center gap-0.5 text-[#1A73E8] hover:underline"
                              >
                                <span>{turn.leadLink.text}</span>
                                <ExternalLink className="w-3.5 h-3.5 inline ml-0.5" />
                              </a>
                              .
                            </>
                          )}
                        </p>

                        {/* Bold Section Heading: "Ce qui a été mis en place :" */}
                        <h3 className="text-[16px] font-semibold text-[#111318] pt-1">
                          {turn.sectionHeading}
                        </h3>

                        {/* Numbered List with inline file chips + indented bullet points */}
                        <ol className="list-decimal pl-5 space-y-4">
                          {turn.items.map((sectionItem, sIdx) => (
                            <li key={sIdx} className="pl-1 space-y-1.5">
                              <div className="text-[#111318]">
                                <strong className="font-semibold">{sectionItem.title}</strong>
                                {sectionItem.chips && sectionItem.chips.length > 0 && (
                                  <span className="font-normal text-[#202124]">
                                    {' ( '}
                                    {sectionItem.chips.map((chip, cIdx) => (
                                      <React.Fragment key={chip.label}>
                                        {cIdx > 0 && <span className="mx-1">&amp;</span>}
                                        <InlineFileChip
                                          chip={chip}
                                          onClick={() =>
                                            turn.filesChanged.length > 0 &&
                                            onOpenInspector({
                                              kind: 'review',
                                              files: turn.filesChanged,
                                            })
                                          }
                                        />
                                      </React.Fragment>
                                    ))}
                                    {' ) :'}
                                  </span>
                                )}
                                {(!sectionItem.chips || sectionItem.chips.length === 0) && ' :'}
                              </div>

                              <ul className="list-disc pl-5 space-y-1 text-[#202124]">
                                {sectionItem.bullets.map((bText, bIdx) => (
                                  <li key={bIdx}>{renderAntigravityInlineText(bText)}</li>
                                ))}
                              </ul>
                            </li>
                          ))}
                        </ol>

                        {turn.codeBlock && <TurnCodeBlockCard block={turn.codeBlock} />}

                        {turn.pubsubInspector && (
                          <PubSubInspectorCard inspector={turn.pubsubInspector} />
                        )}

                        {turn.visualCheck && (
                          <VisualCheckCard
                            visual={turn.visualCheck}
                            onOpenVisualSkill={onOpenVisualSkill}
                            onPreviewDoc={(doc) => setPreviewDoc(doc)}
                          />
                        )}

                        {/* "X files changed +added -removed ›" Card + [Review] button */}
                        {turn.filesChanged.length > 0 && (
                          <div className="pt-2">
                            <div className="flex items-center justify-between px-4 py-3 rounded-2xl bg-white shadow-[0_2px_12px_rgba(0,0,0,0.05)]">
                              <button
                                type="button"
                                onClick={() =>
                                  onOpenInspector({ kind: 'review', files: turn.filesChanged })
                                }
                                className="flex items-center gap-2 text-[14px] text-[#202124] hover:text-black cursor-pointer"
                              >
                                <span>
                                  {turn.filesChanged.length}{' '}
                                  {turn.filesChanged.length === 1 ? 'file' : 'files'} changed
                                </span>
                                <span className="text-[#188038] font-medium">+{totalAdded}</span>
                                <span className="text-[#D93025] font-medium">-{totalRemoved}</span>
                                <ChevronRight className="w-4 h-4 text-[#5F6368]" />
                              </button>

                              <button
                                type="button"
                                onClick={() =>
                                  onOpenInspector({ kind: 'review', files: turn.filesChanged })
                                }
                                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-[#F1F3F5] hover:bg-[#E4E7EB] text-[13px] font-medium text-[#202124] transition-colors cursor-pointer"
                              >
                                <FileDiff className="w-3.5 h-3.5 text-[#5F6368]" />
                                <span>Review</span>
                              </button>
                            </div>
                          </div>
                        )}

                        {/* Timestamp + Copy / ThumbsUp / ThumbsDown */}
                        <div className="flex items-center justify-end gap-3 text-[12.5px] text-[#5F6368] pt-1">
                          <span>just now</span>
                          <Copy className="w-3.5 h-3.5 hover:text-[#202124] cursor-pointer" />
                          <ThumbsUp className="w-3.5 h-3.5 hover:text-[#202124] cursor-pointer" />
                          <ThumbsDown className="w-3.5 h-3.5 hover:text-[#202124] cursor-pointer" />
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div ref={scrollEndRef} />
          </div>
        )}
      </div>

      {/* Bottom Floating Scroll Button + Double-Layered Antigravity Composer */}
      <div className="absolute bottom-0 inset-x-0 px-6 pb-5 pt-4 bg-gradient-to-t from-white via-white/95 to-transparent pointer-events-none">
        <div className="max-w-[760px] mx-auto pointer-events-auto relative">
          {/* Centered circular ↓ button above composer when conversation has turns */}
          {!isEmpty && (
            <div className="flex justify-center mb-3">
              <button
                type="button"
                onClick={() => scrollEndRef.current?.scrollIntoView({ behavior: 'smooth' })}
                className="w-8 h-8 rounded-full bg-white shadow-[0_2px_10px_rgba(0,0,0,0.08)] hover:bg-[#F8F9FA] flex items-center justify-center text-[#5F6368] cursor-pointer"
              >
                <ArrowDown className="w-4 h-4" />
              </button>
            </div>
          )}

          {/* Interactive Antigravity `ask_question` Tray docked directly above composer */}
          {activeAskTurn && activeAskTurn.askQuestions && (
            <AskQuestionTray
              questions={activeAskTurn.askQuestions}
              currentIdx={questionStepIdx}
              selectedChoices={questionChoices}
              otherTexts={questionOtherTexts}
              collapsed={questionCollapsed}
              onChangeIdx={setQuestionStepIdx}
              onSelectChoice={(qId, optIdx) =>
                setQuestionChoices((prev) => ({ ...prev, [qId]: optIdx }))
              }
              onChangeOtherText={(qId, txt) =>
                setQuestionOtherTexts((prev) => ({ ...prev, [qId]: txt }))
              }
              onToggleCollapse={() => setQuestionCollapsed((prev) => !prev)}
              onDismiss={() => setDismissedQuestionTurnId(activeAskTurn.id)}
              onSkip={handleSkipQuestion}
              onContinue={handleContinueQuestion}
            />
          )}

          {/* Discreet Speaker Prompt Chips */}
          {(slashMenuOpen || (nextSuggestedTurn && !isStreaming && !activeAskTurn)) && (
            <div className="flex items-center gap-1.5 overflow-x-auto pb-2">
              {scenario.turns.map((t, idx) => {
                const done = completedIds.has(t.id);
                const isNext = nextSuggestedTurn?.id === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    disabled={isStreaming}
                    onClick={() => handleSelectChip(t, idx)}
                    className={`shrink-0 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[12px] transition-all cursor-pointer ${
                      done
                        ? 'bg-[#F1F3F5] text-[#5F6368]'
                        : isNext
                        ? 'bg-[#202124] text-white font-medium'
                        : 'bg-[#F1F3F5] hover:bg-[#E4E7EB] text-[#3C4043]'
                    }`}
                  >
                    {done && <Check className="w-3 h-3 text-[#188038]" />}
                    <span>{t.chipLabel}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* Outer soft halo + Inner pure white rounded Antigravity composer */}
          <div className="rounded-[28px] bg-[#F3F4F6]/80 p-1.5 shadow-[0_4px_24px_rgba(0,0,0,0.04)]">
            <div className="rounded-[22px] bg-white px-4 py-3 shadow-[0_1px_4px_rgba(0,0,0,0.03)] space-y-2.5">
              {/* Project & Branch row when in empty state */}
              {isEmpty && (
                <div className="flex items-center gap-4 px-1 text-[12.5px] text-[#5F6368]">
                  <span className="inline-flex items-center gap-1.5 hover:text-[#202124] cursor-pointer">
                    <Folder className="w-3.5 h-3.5" />
                    <span>{scenario.projectFolder}</span>
                    <ChevronDown className="w-3 h-3" />
                  </span>
                  <span className="inline-flex items-center gap-1 hover:text-[#202124] cursor-pointer">
                    <GitBranch className="w-3.5 h-3.5" />
                    <span>{scenario.gitBranch}</span>
                    <ChevronDown className="w-3 h-3" />
                  </span>
                </div>
              )}

              {/* Clean white input directly on the card */}
              {(() => {
                const pendingTurn =
                  (selectedTurnIndex !== null && scenario.turns[selectedTurnIndex]) ||
                  nextSuggestedTurn;
                const att = !activeAskTurn ? pendingTurn?.promptAttachment : undefined;
                if (!att) return null;
                return (
                  <div className="px-1 pt-1">
                    <button
                      type="button"
                      onClick={() => setPreviewDoc(att)}
                      title="Cliquer pour inspecter le document joint en plein écran"
                      className="inline-flex items-center gap-2.5 rounded-xl bg-[#F4F6F9] hover:bg-[#ECEFF4] px-2.5 py-1.5 transition-colors cursor-pointer"
                    >
                      <img
                        src={att.imageUrl}
                        alt={att.title}
                        className="w-9 h-6 rounded-md object-cover bg-white shrink-0"
                      />
                      <div className="text-left min-w-0">
                        <div className="text-[12px] font-medium text-[#111318] truncate max-w-[260px]">
                          {att.title}
                        </div>
                        <div className="text-[10.5px] text-[#5F6368] truncate max-w-[260px]">
                          {att.highlightLabel} · Cliquer pour agrandir
                        </div>
                      </div>
                    </button>
                  </div>
                );
              })()}

              <div className="px-1 pt-0.5">
                <textarea
                  ref={textareaRef}
                  rows={inputValue.length > 180 ? 3 : inputValue.length > 90 ? 2 : 1}
                  value={inputValue}
                  onChange={handleInputChange}
                  onKeyDown={handleKeyDown}
                  placeholder="Ask anything, @ to mention, / for actions"
                  className="w-full resize-none bg-transparent text-[15px] text-[#202124] placeholder:text-[#70757A] focus:outline-none leading-relaxed"
                />
              </div>

              {/* Bottom Controls Row */}
              <div className="flex items-center justify-between px-0.5 pt-0.5">
                <div className="flex items-center gap-2.5 text-[13px] text-[#3C4043]">
                  <button
                    type="button"
                    onClick={() => setSlashMenuOpen(!slashMenuOpen)}
                    title="Afficher / masquer les prompts préparés"
                    className="w-6 h-6 rounded-full hover:bg-[#F1F3F5] flex items-center justify-center text-[#5F6368] cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                  </button>

                  {/* Model Selector: Gemini 4 - Carbon, Gemini 4 - Hydrogen, Claude Sonnet 5.5 */}
                  <div className="relative">
                    <button
                      type="button"
                      onClick={() => setModelMenuOpen(!modelMenuOpen)}
                      className="inline-flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-[#F1F3F5] text-[#202124] font-medium transition-colors cursor-pointer"
                    >
                      <span>{selectedModel}</span>
                      <ChevronUp
                        className={`w-3.5 h-3.5 text-[#70757A] transition-transform ${
                          modelMenuOpen ? 'rotate-180' : ''
                        }`}
                      />
                    </button>

                    {modelMenuOpen && (
                      <div className="absolute left-0 bottom-full mb-2 w-56 p-1.5 rounded-2xl bg-white shadow-[0_10px_32px_rgba(15,23,42,0.12)] z-40 animate-fade-slide-up">
                        {AVAILABLE_MODELS.map((model) => {
                          const active = selectedModel === model;
                          return (
                            <button
                              key={model}
                              type="button"
                              onClick={() => {
                                setSelectedModel(model);
                                setModelMenuOpen(false);
                              }}
                              className={`w-full flex items-center justify-between px-3 py-2 rounded-xl text-[13px] transition-colors cursor-pointer ${
                                active
                                  ? 'bg-[#F1F3F5] text-[#111318] font-medium'
                                  : 'text-[#3C4043] hover:bg-[#F8F9FA]'
                              }`}
                            >
                              <span>{model}</span>
                              {active && <Check className="w-3.5 h-3.5 text-[#111318]" />}
                            </button>
                          );
                        })}
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <span className="inline-flex items-center gap-1 text-[13px] text-[#5F6368]">
                    <ShieldAlert className="w-3.5 h-3.5" />
                    <span>Turbo</span>
                    <ChevronUp className="w-3.5 h-3.5 text-[#70757A]" />
                  </span>

                  <button
                    type="button"
                    className="w-7 h-7 rounded-full hover:bg-[#F1F3F5] flex items-center justify-center text-[#5F6368] cursor-pointer"
                  >
                    <Mic className="w-4 h-4" />
                  </button>

                  <button
                    type="button"
                    onClick={handleSubmit}
                    disabled={isStreaming}
                    title="Envoyer"
                    className="w-8 h-8 rounded-full bg-[#111318] hover:bg-[#272B35] disabled:opacity-40 text-white flex items-center justify-center transition-all cursor-pointer"
                  >
                    {inputValue.trim() ? <ArrowUp className="w-4 h-4" /> : <VoiceSparkleIcon />}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Full-Resolution PDF / Diagram Lightbox Preview */}
      {previewDoc && (
        <div
          onClick={() => setPreviewDoc(null)}
          className="fixed inset-0 z-50 bg-black/50 backdrop-blur-[2px] flex items-center justify-center p-6 animate-fade-slide-up"
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="max-w-5xl w-full max-h-[92vh] rounded-2xl bg-white shadow-2xl overflow-hidden flex flex-col"
          >
            <div className="flex items-center justify-between gap-4 px-5 py-3.5 border-b border-[#ECEEF2]">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span
                    className={`px-2 py-0.5 rounded-md font-mono text-[11px] font-medium ${badgeSurfaceClass(
                      previewDoc.tone
                    )}`}
                  >
                    {previewDoc.metaBadge}
                  </span>
                  <h3 className="text-[14.5px] font-semibold text-[#111318] truncate">
                    {previewDoc.title}
                  </h3>
                  <span className="font-mono text-[12px] font-semibold text-[#202124]">
                    · {previewDoc.highlightLabel}
                  </span>
                </div>
                <p className="font-mono text-[11.5px] text-[#5F6368] truncate mt-0.5">
                  {previewDoc.uri}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setPreviewDoc(null)}
                className="w-8 h-8 rounded-full bg-[#F1F3F5] hover:bg-[#E4E7EB] flex items-center justify-center text-[#3C4043] cursor-pointer shrink-0"
                title="Fermer l'aperçu"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto bg-[#ECEFF3] p-5 flex justify-center">
              <img
                src={previewDoc.imageUrl}
                alt={previewDoc.title}
                className="max-w-full h-auto rounded-xl shadow-[0_8px_30px_rgba(15,23,42,0.14)] bg-white"
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
