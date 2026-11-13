import React from 'react';
import {
  FilePlus2,
  File,
  SquareTerminal,
  Puzzle,
  ChevronRight,
  FileText,
  MoreVertical,
  X,
  CheckCircle2,
} from 'lucide-react';
import {
  ArtifactItem,
  BackgroundTaskItem,
  FileDiffItem,
  SubagentItem,
} from '../types';

export type InspectorModalState =
  | { kind: 'review'; files: FileDiffItem[] }
  | { kind: 'files'; files: FileDiffItem[] }
  | { kind: 'terminal'; logs: string[] }
  | { kind: 'subagents'; subagents: SubagentItem[] }
  | { kind: 'artifact'; artifact: ArtifactItem }
  | null;

interface OverviewPanelProps {
  files: FileDiffItem[];
  terminalLogs: string[];
  subagents: SubagentItem[];
  backgroundTasks: BackgroundTaskItem[];
  artifacts: ArtifactItem[];
  isStreaming: boolean;
  onOpenInspector: (modal: InspectorModalState) => void;
  onOpenCustomizations: () => void;
}

export const OverviewPanel: React.FC<OverviewPanelProps> = ({
  files,
  terminalLogs,
  subagents,
  backgroundTasks,
  artifacts,
  isStreaming,
  onOpenInspector,
  onOpenCustomizations,
}) => {
  const subagentCount = isStreaming ? Math.max(1, subagents.length) : subagents.length;
  const bgTaskCount = isStreaming ? Math.max(1, backgroundTasks.length) : backgroundTasks.length;

  return (
    <aside className="w-[300px] shrink-0 pt-2 pr-5 pb-4 select-none">
      {/* Pixel-faithful floating Overview card matching media_1794580218010.png */}
      <div className="rounded-2xl bg-white shadow-[0_2px_18px_rgba(15,23,42,0.06)] overflow-hidden divide-y divide-[#F1F3F5]">
        {/* Section 1: Overview + 4 navigation rows */}
        <div className="p-3.5">
          <div className="flex items-center justify-between px-2 mb-2">
            <span className="text-[13px] font-medium text-[#70757A]">Overview</span>
            <MoreVertical className="w-3.5 h-3.5 text-[#70757A]" />
          </div>

          <div className="space-y-0.5">
            <button
              type="button"
              onClick={() => onOpenInspector({ kind: 'review', files })}
              className="w-full flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-[#F8F9FA] text-[14px] text-[#202124] transition-colors cursor-pointer"
            >
              <FilePlus2 className="w-4 h-4 text-[#5F6368] shrink-0" />
              <span>Review</span>
            </button>

            <button
              type="button"
              onClick={() => onOpenInspector({ kind: 'files', files })}
              className="w-full flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-[#F8F9FA] text-[14px] text-[#202124] transition-colors cursor-pointer"
            >
              <File className="w-4 h-4 text-[#5F6368] shrink-0" />
              <span>Files</span>
            </button>

            <button
              type="button"
              onClick={() => onOpenInspector({ kind: 'terminal', logs: terminalLogs })}
              className="w-full flex items-center gap-3 px-2 py-2 rounded-xl hover:bg-[#F8F9FA] text-[14px] text-[#202124] transition-colors cursor-pointer"
            >
              <SquareTerminal className="w-4 h-4 text-[#5F6368] shrink-0" />
              <span>Terminal</span>
            </button>

            <button
              type="button"
              onClick={onOpenCustomizations}
              className="w-full flex items-center justify-between px-2 py-2 rounded-xl hover:bg-[#F8F9FA] text-[14px] text-[#202124] transition-colors cursor-pointer"
            >
              <span className="flex items-center gap-3">
                <Puzzle className="w-4 h-4 text-[#5F6368] shrink-0" />
                <span>Extensions</span>
              </span>
              <ChevronRight className="w-3.5 h-3.5 text-[#70757A]" />
            </button>
          </div>
        </div>

        {/* Section 2: Compact Subagents row */}
        <button
          type="button"
          onClick={() => subagents.length > 0 && onOpenInspector({ kind: 'subagents', subagents })}
          className="w-full px-5 py-3 flex items-center gap-2 hover:bg-[#F8F9FA] text-left transition-colors cursor-pointer"
        >
          <span className="text-[13px] font-medium text-[#70757A]">Subagents</span>
          <span className="px-2 py-0.5 rounded-full bg-[#F3F4F6] text-[12px] font-medium text-[#5F6368]">
            {subagentCount}
          </span>
        </button>

        {/* Section 3: Compact Background Tasks row */}
        <button
          type="button"
          onClick={() =>
            terminalLogs.length > 0 && onOpenInspector({ kind: 'terminal', logs: terminalLogs })
          }
          className="w-full px-5 py-3 flex items-center gap-2 hover:bg-[#F8F9FA] text-left transition-colors cursor-pointer"
        >
          <span className="text-[13px] font-medium text-[#70757A]">Background Tasks</span>
          <span className="px-2 py-0.5 rounded-full bg-[#F3F4F6] text-[12px] font-medium text-[#5F6368]">
            {bgTaskCount}
          </span>
        </button>

        {/* Section 4: Artifacts */}
        <div className="px-5 py-3.5">
          <div className="flex items-center gap-2">
            <span className="text-[13px] font-medium text-[#70757A]">Artifacts</span>
            <span className="px-2 py-0.5 rounded-full bg-[#F3F4F6] text-[12px] font-medium text-[#5F6368]">
              {artifacts.length}
            </span>
          </div>

          {artifacts.length > 0 && (
            <div className="mt-2.5 -mx-2 space-y-0.5">
              {artifacts.map((art) => (
                <button
                  key={art.id}
                  type="button"
                  onClick={() => onOpenInspector({ kind: 'artifact', artifact: art })}
                  className="w-full flex items-center gap-2.5 px-2 py-2 rounded-xl hover:bg-[#F8F9FA] text-left text-[14px] text-[#202124] transition-colors cursor-pointer"
                >
                  <FileText className="w-4 h-4 text-[#5F6368] shrink-0" />
                  <span className="truncate">{art.title}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};

interface InspectorDrawerProps {
  modal: InspectorModalState;
  onClose: () => void;
}

export const InspectorDrawer: React.FC<InspectorDrawerProps> = ({ modal, onClose }) => {
  if (!modal) return null;

  const toneSurface = (tone?: 'neutral' | 'warning' | 'positive' | 'ruby') => {
    switch (tone) {
      case 'positive':
        return 'bg-emerald-500/10 text-emerald-900';
      case 'warning':
        return 'bg-amber-500/12 text-amber-900';
      case 'ruby':
        return 'bg-rose-500/10 text-rose-900';
      default:
        return 'bg-[#F4F5F8] text-[#111318]';
    }
  };

  return (
    <div
      onClick={onClose}
      className="fixed inset-0 z-50 bg-black/20 backdrop-blur-[2px] flex justify-end"
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="w-full max-w-2xl bg-white h-full shadow-2xl flex flex-col animate-fade-slide-up"
      >
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#ECEEF2]">
          <div>
            <h2 className="text-[15px] font-semibold text-[#111318]">
              {modal.kind === 'review' && 'Review Changes'}
              {modal.kind === 'files' && 'Workspace Files — data-days-demo'}
              {modal.kind === 'terminal' && 'Terminal — data-days-demo (europe-west1)'}
              {modal.kind === 'subagents' && 'Active & Completed Subagents'}
              {modal.kind === 'artifact' && modal.artifact.title}
            </h2>
            {modal.kind === 'artifact' && (
              <p className="text-[12px] text-[#6B7280]">{modal.artifact.subtitle}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="w-8 h-8 rounded-full hover:bg-[#F3F4F7] flex items-center justify-center text-[#6B7280] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6 space-y-5">
          {(modal.kind === 'review' || modal.kind === 'files') &&
            (modal.files.length === 0 ? (
              <p className="text-[14px] text-[#5F6368]">Aucun fichier modifié pour le moment.</p>
            ) : (
              modal.files.map((file) => (
                <div key={file.path} className="rounded-2xl bg-[#F7F8FA] overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#E6E8EE]">
                    <span className="font-mono text-[12px] font-medium text-[#111318]">
                      {file.path}
                    </span>
                    <span className="font-mono text-[11.5px] text-[#188038] font-medium">
                      +{file.added} <span className="text-[#D93025]">-{file.removed}</span>
                    </span>
                  </div>
                  <pre className="p-4 text-[12px] font-mono text-[#1F2937] overflow-x-auto leading-relaxed">
                    {file.content}
                  </pre>
                </div>
              ))
            ))}

          {modal.kind === 'terminal' && (
            <div className="rounded-2xl bg-[#111318] text-[#E5E7EB] p-5 font-mono text-[12px] leading-relaxed space-y-1.5">
              {modal.logs.length === 0 ? (
                <div className="text-[#9CA3AF]">$ Ready on project data-days-demo (europe-west1)</div>
              ) : (
                modal.logs.map((line, idx) => (
                  <div
                    key={idx}
                    className={
                      line.startsWith('$')
                        ? 'text-[#93C5FD] font-medium pt-2 first:pt-0'
                        : line.includes('[FAIL]')
                        ? 'text-[#FDA4AF]'
                        : line.includes('[WARN]')
                        ? 'text-[#FDE68A]'
                        : 'text-[#D1D5DB]'
                    }
                  >
                    {line}
                  </div>
                ))
              )}
            </div>
          )}

          {modal.kind === 'subagents' && (
            <div className="space-y-3">
              {modal.subagents.map((sa) => (
                <div
                  key={sa.id}
                  className="p-4 rounded-2xl bg-[#F8F9FA] flex items-center justify-between"
                >
                  <div>
                    <div className="text-[14px] font-semibold text-[#111318]">{sa.role}</div>
                    <div className="text-[12.5px] font-mono text-[#5F6368] mt-0.5">
                      Skill: {sa.skill}
                    </div>
                  </div>
                  <CheckCircle2 className="w-4 h-4 text-[#188038]" />
                </div>
              ))}
            </div>
          )}

          {modal.kind === 'artifact' && (
            <div className="space-y-6">
              <h3 className="text-[17px] font-semibold text-[#111318]">
                {modal.artifact.markdownSummary.heading}
              </h3>

              {modal.artifact.markdownSummary.metrics && (
                <div className="grid grid-cols-2 gap-3">
                  {modal.artifact.markdownSummary.metrics.map((m) => (
                    <div key={m.label} className={`p-4 rounded-2xl ${toneSurface(m.tone)}`}>
                      <div className="text-[11.5px] opacity-75 font-medium">{m.label}</div>
                      <div className="text-[20px] font-bold tracking-tight mt-1">{m.value}</div>
                    </div>
                  ))}
                </div>
              )}

              <div className="p-5 rounded-2xl bg-[#F7F8FA] space-y-2.5">
                {modal.artifact.markdownSummary.bullets.map((b, i) => (
                  <div key={i} className="flex items-start gap-2.5 text-[13.5px] text-[#374151]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#111318] mt-2 shrink-0" />
                    <span>{b}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
