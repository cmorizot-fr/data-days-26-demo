import React, { useState } from 'react';
import { BarChart3, CheckCircle2, Eye } from 'lucide-react';
import { VisualCheckBlock, VisualCheckDocPreview, VisualTone } from '../types';

/**
 * Palette for visual audit widgets (strictly zero colored borders/rings:
 * hierarchy relies exclusively on surface luminance, soft tinted fills, and typography).
 */
const TONE: Record<
  VisualTone,
  { label: string; fill: string; text: string; softBg: string }
> = {
  positive: {
    label: 'OK',
    fill: 'bg-[#16A34A]',
    text: 'text-[#15803D]',
    softBg: 'bg-[#ECFDF5]',
  },
  warning: {
    label: 'À surveiller',
    fill: 'bg-[#D97706]',
    text: 'text-[#B45309]',
    softBg: 'bg-[#FFFBEB]',
  },
  ruby: {
    label: 'Alerte',
    fill: 'bg-[#DC2626]',
    text: 'text-[#B91C1C]',
    softBg: 'bg-[#FEF2F2]',
  },
  blue: {
    label: 'Info',
    fill: 'bg-[#2563EB]',
    text: 'text-[#1D4ED8]',
    softBg: 'bg-[#EFF6FF]',
  },
  neutral: {
    label: 'Neutre',
    fill: 'bg-[#64748B]',
    text: 'text-[#475569]',
    softBg: 'bg-[#F1F5F9]',
  },
};

const PILL_BASE =
  'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium transition-colors cursor-pointer';
const PILL_ACTIVE = 'bg-[#1F2937] text-white';
const PILL_IDLE = 'bg-[#F1F3F5] text-[#4B5563] hover:bg-[#E5E7EB]';

/**
 * Inline Generative UI visual validation card driven by `bq-visual-audit` + MCP `data-agent-kit/render_chart`.
 * Uses layered neutral surfaces (#F6F7F9 -> #FFFFFF), soft tinted pills, and subtle elevation with
 * strictly zero colored borders or rings.
 */
export const VisualCheckCard: React.FC<{
  visual: VisualCheckBlock;
  onOpenVisualSkill: () => void;
  onPreviewDoc: (doc: VisualCheckDocPreview) => void;
}> = ({ visual, onOpenVisualSkill, onPreviewDoc }) => {
  const bars = visual.bars ?? [];
  const kpis = visual.kpis ?? [];
  const documents = visual.documents ?? [];
  const hasChart = bars.length > 0;

  // One filter pill per tone actually used by the rows, in order of first appearance.
  const tones = bars.reduce<VisualTone[]>((acc, row) => {
    const tone = row.tone ?? 'blue';
    return acc.includes(tone) ? acc : [...acc, tone];
  }, []);

  const [toneFilter, setToneFilter] = useState<VisualTone | 'all'>('all');
  const [selectedIdx, setSelectedIdx] = useState(0);

  const activeTone = toneFilter !== 'all' && tones.includes(toneFilter) ? toneFilter : 'all';
  const visibleRows = bars
    .map((row, idx) => ({ row, idx }))
    .filter(({ row }) => activeTone === 'all' || (row.tone ?? 'blue') === activeTone);
  const selected = visibleRows.find(({ idx }) => idx === selectedIdx) ?? visibleRows[0];
  const selectedTone = selected ? TONE[selected.row.tone ?? 'blue'] : undefined;

  return (
    <div className="mt-5 rounded-2xl bg-[#F6F7F9] p-5 space-y-4 select-none">
      {/* Header Row */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-white shadow-[0_1px_3px_rgba(15,23,42,0.06)] flex items-center justify-center shrink-0 mt-0.5">
            <BarChart3 className="w-4 h-4 text-[#1A73E8]" />
          </div>
          <div className="min-w-0">
            <div className="text-[14.5px] font-semibold text-[#111318] leading-snug">
              {visual.title}
            </div>
            {visual.subtitle && (
              <p className="text-[12.5px] text-[#5F6368] leading-snug mt-0.5">{visual.subtitle}</p>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={onOpenVisualSkill}
          title="Inspecter le skill Workspace bq-visual-audit dans Customizations"
          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-white hover:bg-[#ECEEF2] shadow-[0_1px_2px_rgba(15,23,42,0.04)] font-mono text-[11.5px] text-[#3C4043] transition-colors cursor-pointer shrink-0"
        >
          <span className="w-1.5 h-1.5 rounded-full bg-[#16A34A]" />
          <span>{visual.skillBadge ?? 'bq-visual-audit · render_chart'}</span>
        </button>
      </div>

      {/* KPI Surface Tiles */}
      {kpis.length > 0 && (
        <div
          className={`grid gap-2.5 ${
            kpis.length === 3
              ? 'grid-cols-1 sm:grid-cols-3'
              : kpis.length === 2
              ? 'grid-cols-2'
              : 'grid-cols-2 sm:grid-cols-4'
          }`}
        >
          {kpis.map((kpi, idx) => {
            const kpiTone = TONE[kpi.tone ?? 'neutral'];
            return (
              <div
                key={idx}
                className="rounded-xl bg-white px-3.5 py-3 shadow-[0_1px_2px_rgba(15,23,42,0.04)] flex flex-col justify-between min-w-0"
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-[11.5px] font-medium text-[#5F6368] truncate">
                    {kpi.label}
                  </span>
                  <span className={`w-2 h-2 rounded-full shrink-0 ${kpiTone.fill}`} />
                </div>
                <div
                  className={`font-mono text-[18px] font-semibold tracking-tight mt-1.5 leading-none ${
                    kpi.tone === 'ruby' ? 'text-[#B91C1C]' : 'text-[#111318]'
                  }`}
                >
                  {kpi.value}
                </div>
                {kpi.sublabel && (
                  <div className="text-[11px] text-[#70757A] leading-tight mt-1.5 truncate">
                    {kpi.sublabel}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Interactive Chart Card */}
      {hasChart && (
        <div className="rounded-xl bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)] space-y-3">
          {/* Chart Header + Tone Filters */}
          <div className="flex flex-wrap items-center justify-between gap-2.5 pb-3 border-b border-[#F1F3F5]">
            {visual.chartTitle && (
              <p className="text-[13px] font-semibold text-[#111318] leading-snug">
                {visual.chartTitle}
              </p>
            )}

            {tones.length > 1 && (
              <div className="flex flex-wrap items-center gap-1.5">
                <button
                  type="button"
                  aria-pressed={activeTone === 'all'}
                  onClick={() => setToneFilter('all')}
                  className={`${PILL_BASE} ${activeTone === 'all' ? PILL_ACTIVE : PILL_IDLE}`}
                >
                  Toutes ({bars.length})
                </button>
                {tones.map((tone) => {
                  const isActive = activeTone === tone;
                  return (
                    <button
                      key={tone}
                      type="button"
                      aria-pressed={isActive}
                      onClick={() => setToneFilter(tone)}
                      className={`${PILL_BASE} ${isActive ? PILL_ACTIVE : PILL_IDLE}`}
                    >
                      <span
                        className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-white' : TONE[tone].fill}`}
                      />
                      {TONE[tone].label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          {/* Horizontal Bar Rows */}
          <div className="space-y-1">
            {visibleRows.map(({ row, idx }) => {
              const tone = TONE[row.tone ?? 'blue'];
              const isSelected = selected?.idx === idx;
              return (
                <button
                  key={idx}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setSelectedIdx(idx)}
                  title={row.label}
                  className={`w-full grid grid-cols-[minmax(0,44%)_minmax(0,1fr)_max-content] items-center gap-x-4 px-3 py-2 rounded-xl text-left transition-colors cursor-pointer ${
                    isSelected ? 'bg-[#F3F5F8]' : 'hover:bg-[#F9FAFB]'
                  }`}
                >
                  <div className="min-w-0 flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${tone.fill}`} />
                    <div className="min-w-0">
                      <div
                        className={`truncate text-[13px] leading-snug ${
                          isSelected ? 'font-semibold text-[#111318]' : 'font-medium text-[#27272A]'
                        }`}
                      >
                        {row.label}
                      </div>
                    </div>
                    {row.badge && (
                      <span
                        className={`shrink-0 px-2 py-0.5 rounded-full text-[10.5px] font-semibold ${tone.softBg} ${tone.text}`}
                      >
                        {row.badge}
                      </span>
                    )}
                  </div>

                  <div className="h-2.5 w-full rounded-full bg-[#F1F3F5] overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${tone.fill}`}
                      style={{ width: `${Math.max(3, Math.min(100, row.pct))}%` }}
                    />
                  </div>

                  <span
                    className={`font-mono text-[13px] text-right whitespace-nowrap tabular-nums ${
                      isSelected ? 'font-semibold text-[#111318]' : 'font-medium text-[#3C4043]'
                    }`}
                  >
                    {row.valueLabel}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Selected Row Insight Strip */}
          {selected && selectedTone && (
            <div className="rounded-xl bg-[#F7F8FA] px-3.5 py-2.5 flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span
                  className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-semibold shrink-0 ${selectedTone.softBg} ${selectedTone.text}`}
                >
                  <span className={`w-1.5 h-1.5 rounded-full ${selectedTone.fill}`} />
                  <span>{selectedTone.label}</span>
                </span>
                <span className="text-[12.5px] font-medium text-[#111318] truncate">
                  {selected.row.label}
                </span>
                {selected.row.sublabel && (
                  <span className="text-[12px] text-[#5F6368] truncate">
                    — {selected.row.sublabel}
                  </span>
                )}
              </div>
              <span className="font-mono text-[12.5px] font-semibold text-[#111318] whitespace-nowrap">
                {selected.row.valueLabel}
                {selected.row.badge ? ` (${selected.row.badge})` : ''}
              </span>
            </div>
          )}
        </div>
      )}

      {/* Document Gallery (ObjectRef PDF previews) */}
      {documents.length > 0 && (
        <div className="rounded-xl bg-white p-4 shadow-[0_1px_2px_rgba(15,23,42,0.04)] space-y-3">
          {visual.documentsTitle && (
            <div className="flex items-baseline justify-between gap-4">
              <span className="text-[13px] font-semibold text-[#111318] leading-snug">
                {visual.documentsTitle}
              </span>
              <span className="font-mono text-[11.5px] text-[#5F6368] shrink-0">
                Cliquer pour agrandir
              </span>
            </div>
          )}

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {documents.map((doc) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => onPreviewDoc(doc)}
                className="group rounded-xl bg-[#F6F7F9] hover:bg-[#ECEEF2] p-2.5 transition-colors cursor-pointer text-left flex flex-col justify-between"
              >
                <div>
                  <div className="relative rounded-lg bg-white overflow-hidden aspect-[210/285] mb-2">
                    <img
                      src={doc.imageUrl}
                      alt={doc.title}
                      className="w-full h-full object-cover object-top group-hover:scale-[1.03] transition-transform duration-300"
                    />
                    <span className="opacity-0 group-hover:opacity-100 transition-opacity absolute bottom-2 right-2 inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-black/70 text-white text-[10.5px] font-medium">
                      <Eye className="w-3 h-3" />
                      <span>Zoom</span>
                    </span>
                  </div>

                  <div className="font-mono text-[10.5px] text-[#5F6368] truncate">
                    {doc.metaBadge}
                  </div>
                  <div className="text-[12px] font-semibold text-[#111318] leading-snug mt-1 line-clamp-1">
                    {doc.title}
                  </div>
                  <div className="text-[11px] text-[#5F6368] leading-tight mt-0.5 line-clamp-1">
                    {doc.subtitle}
                  </div>
                </div>

                <div className="flex items-center gap-1.5 pt-2 mt-1.5 font-mono text-[11px] font-semibold text-[#111318]">
                  <span
                    className={`w-1.5 h-1.5 rounded-full shrink-0 ${TONE[doc.tone ?? 'neutral'].fill}`}
                  />
                  <span className="truncate">{doc.highlightLabel}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Footer Verification Banner */}
      {visual.footerNote && (
        <div className="rounded-xl bg-[#ECFDF5] px-3.5 py-2.5 flex items-start gap-2 text-[12px] text-[#14532D] leading-relaxed">
          <CheckCircle2 className="w-4 h-4 text-[#16A34A] shrink-0 mt-0.5" />
          <span>{visual.footerNote}</span>
        </div>
      )}
    </div>
  );
};
