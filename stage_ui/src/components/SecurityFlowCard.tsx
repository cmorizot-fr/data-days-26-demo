import React from 'react';
import { ArrowRight, ArrowRightLeft, Lock, ShieldCheck } from 'lucide-react';
import { SecurityFlowBlock, VisualTone } from '../types';

/**
 * Surface-luminance palette (strictly zero colored borders, rings, or strokes around cards/pills).
 */
const TONE_SURFACE: Record<
  VisualTone,
  { pillBg: string; pillText: string; numBg: string; numText: string }
> = {
  positive: {
    pillBg: 'bg-[#ECFDF5]',
    pillText: 'text-[#15803D]',
    numBg: 'bg-[#ECFDF5]',
    numText: 'text-[#15803D]',
  },
  blue: {
    pillBg: 'bg-[#EFF6FF]',
    pillText: 'text-[#1D4ED8]',
    numBg: 'bg-[#EFF6FF]',
    numText: 'text-[#1D4ED8]',
  },
  warning: {
    pillBg: 'bg-[#FFFBEB]',
    pillText: 'text-[#B45309]',
    numBg: 'bg-[#FFFBEB]',
    numText: 'text-[#B45309]',
  },
  ruby: {
    pillBg: 'bg-[#FEF2F2]',
    pillText: 'text-[#B91C1C]',
    numBg: 'bg-[#FEF2F2]',
    numText: 'text-[#B91C1C]',
  },
  neutral: {
    pillBg: 'bg-[#F1F5F9]',
    pillText: 'text-[#475569]',
    numBg: 'bg-[#111318]',
    numText: 'text-white',
  },
};

export const SecurityFlowCard: React.FC<{ flow: SecurityFlowBlock }> = ({ flow }) => {
  return (
    <div className="mt-4 rounded-2xl bg-[#F6F7F9] p-4 space-y-4 select-text">
      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-[#15803D] shrink-0" />
            <span className="text-[14px] font-semibold text-[#111318]">{flow.title}</span>
          </div>
          {flow.subtitle && (
            <p className="text-[12px] text-[#5F6368] pl-6">{flow.subtitle}</p>
          )}
        </div>
        {flow.badge && (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-[#ECFDF5] text-[#15803D] text-[11px] font-semibold tracking-tight">
            <Lock className="w-3 h-3" />
            <span>{flow.badge}</span>
          </span>
        )}
      </div>

      {/* 3-Zone Architecture Swimlane */}
      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr_auto_1fr] items-stretch gap-2">
        {flow.nodes.map((node, idx) => {
          const t = TONE_SURFACE[node.tone ?? 'blue'];
          const isCenterBridge = idx === 1 && flow.nodes.length === 3;
          return (
            <React.Fragment key={node.id}>
              <div
                className={`rounded-xl p-3.5 flex flex-col justify-between gap-2 ${
                  isCenterBridge
                    ? 'bg-[#111318] text-white'
                    : 'bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] text-[#111318]'
                }`}
              >
                <div className="space-y-1.5">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10.5px] font-semibold ${
                      isCenterBridge ? 'bg-white/12 text-[#E2E8F0]' : `${t.pillBg} ${t.pillText}`
                    }`}
                  >
                    {node.zoneLabel}
                  </span>
                  <div
                    className={`text-[13px] font-semibold leading-snug ${
                      isCenterBridge ? 'text-white' : 'text-[#111318]'
                    }`}
                  >
                    {node.title}
                  </div>
                  <div
                    className={`font-mono text-[11px] break-all leading-tight ${
                      isCenterBridge ? 'text-[#93C5FD]' : 'text-[#334155]'
                    }`}
                  >
                    {node.subtitle}
                  </div>
                </div>
                <div
                  className={`text-[11px] pt-1 ${
                    isCenterBridge ? 'text-[#94A3B8]' : 'text-[#5F6368]'
                  }`}
                >
                  {node.detail}
                </div>
              </div>

              {idx < flow.nodes.length - 1 && (
                <div className="hidden md:flex items-center justify-center px-0.5 text-[#64748B]">
                  <ArrowRightLeft className="w-4 h-4" />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Step-by-step Secured Sequence */}
      <div className="rounded-xl bg-white shadow-[0_1px_2px_rgba(15,23,42,0.04)] divide-y divide-[#ECEEF2]">
        {flow.steps.map((st) => {
          const t = TONE_SURFACE[st.tone ?? 'blue'];
          return (
            <div key={st.stepNumber} className="px-3.5 py-2.5 flex items-start gap-3">
              <span
                className={`w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[11.5px] font-bold mt-0.5 ${t.numBg} ${t.numText}`}
              >
                {st.stepNumber}
              </span>
              <div className="min-w-0 flex-1 space-y-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-[12.5px] font-semibold text-[#111318]">{st.title}</span>
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-[#F1F5F9] text-[#334155] font-mono text-[10.5px]">
                    <span>{st.fromLabel}</span>
                    <ArrowRight className="w-2.5 h-2.5 text-[#64748B]" />
                    <span>{st.toLabel}</span>
                  </span>
                  <span
                    className={`px-2 py-0.5 rounded-md text-[10.5px] font-semibold ${t.pillBg} ${t.pillText}`}
                  >
                    {st.protocolBadge}
                  </span>
                </div>
                <p className="text-[12px] text-[#4B5563] leading-relaxed">{st.detail}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom Security Guarantees */}
      {flow.guarantees && flow.guarantees.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 pt-0.5">
          {flow.guarantees.map((g, i) => {
            const t = TONE_SURFACE[g.tone ?? 'positive'];
            return (
              <span
                key={i}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11.5px] font-medium ${t.pillBg} ${t.pillText}`}
              >
                {g.label}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
};
