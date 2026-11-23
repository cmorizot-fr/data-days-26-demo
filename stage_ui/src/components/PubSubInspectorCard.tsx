import React, { useState } from 'react';
import { Braces, Check, Copy, Layers, Radio } from 'lucide-react';
import { PubSubInspectorBlock, VisualTone } from '../types';

const TONE_SURFACE: Record<VisualTone, { dot: string; text: string; bg: string }> = {
  positive: { dot: 'bg-[#16A34A]', text: 'text-[#15803D]', bg: 'bg-[#ECFDF5]' },
  warning: { dot: 'bg-[#D97706]', text: 'text-[#B45309]', bg: 'bg-[#FFFBEB]' },
  ruby: { dot: 'bg-[#DC2626]', text: 'text-[#B91C1C]', bg: 'bg-[#FEF2F2]' },
  blue: { dot: 'bg-[#2563EB]', text: 'text-[#1D4ED8]', bg: 'bg-[#EFF6FF]' },
  neutral: { dot: 'bg-[#64748B]', text: 'text-[#475569]', bg: 'bg-[#F1F5F9]' },
};

/**
 * Interactive Cloud Pub/Sub Queue & Nested Payload Explorer.
 * Strictly zero colored borders or rings: visual hierarchy uses surface luminance,
 * soft tinted fills, and monospace typography.
 */
export const PubSubInspectorCard: React.FC<{ inspector: PubSubInspectorBlock }> = ({
  inspector,
}) => {
  const topics = inspector.topics ?? [];
  const [activeTopicIdx, setActiveTopicIdx] = useState(0);
  const [activeSampleIdx, setActiveSampleIdx] = useState(0);
  const [viewMode, setViewMode] = useState<'struct' | 'json'>('struct');
  const [copied, setCopied] = useState(false);

  if (topics.length === 0) return null;

  const safeTopicIdx = activeTopicIdx < topics.length ? activeTopicIdx : 0;
  const activeTopic = topics[safeTopicIdx];
  const samples = activeTopic.samples ?? [];
  const safeSampleIdx = activeSampleIdx < samples.length ? activeSampleIdx : 0;
  const activeSample = samples[safeSampleIdx];

  const handleSelectTopic = (idx: number) => {
    setActiveTopicIdx(idx);
    setActiveSampleIdx(0);
  };

  const handleCopyJson = () => {
    if (!activeSample) return;
    navigator.clipboard?.writeText(activeSample.rawJson);
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  return (
    <div className="mt-5 rounded-2xl bg-[#F6F7F9] p-5 space-y-4 select-none">
      {/* Header Row + View Toggle (Blocs STRUCT | JSON brut) */}
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3 min-w-0">
          <div className="w-9 h-9 rounded-xl bg-white shadow-[0_1px_3px_rgba(15,23,42,0.06)] flex items-center justify-center shrink-0 mt-0.5">
            <Radio className="w-4 h-4 text-[#1A73E8]" />
          </div>
          <div className="min-w-0">
            <div className="text-[14.5px] font-semibold text-[#111318] leading-snug">
              {inspector.title}
            </div>
            {inspector.subtitle && (
              <p className="text-[12.5px] text-[#5F6368] leading-snug mt-0.5">
                {inspector.subtitle}
              </p>
            )}
          </div>
        </div>

        {/* Segmented toggle using pure surface luminance */}
        <div className="inline-flex items-center p-0.5 rounded-full bg-white shadow-[0_1px_2px_rgba(15,23,42,0.05)] text-[12px]">
          <button
            type="button"
            onClick={() => setViewMode('struct')}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-medium transition-colors cursor-pointer ${
              viewMode === 'struct'
                ? 'bg-[#1F2937] text-white'
                : 'text-[#5F6368] hover:text-[#111318]'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Vue structurée</span>
          </button>
          <button
            type="button"
            onClick={() => setViewMode('json')}
            className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full font-medium transition-colors cursor-pointer ${
              viewMode === 'json'
                ? 'bg-[#1F2937] text-white'
                : 'text-[#5F6368] hover:text-[#111318]'
            }`}
          >
            <Braces className="w-3.5 h-3.5" />
            <span>JSON brut</span>
          </button>
        </div>
      </div>

      {/* Topic Selector Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {topics.map((topic, idx) => {
          const isSelected = idx === safeTopicIdx;
          const toneStyle = TONE_SURFACE[topic.tone ?? 'blue'];
          return (
            <button
              key={topic.id}
              type="button"
              onClick={() => handleSelectTopic(idx)}
              className={`rounded-xl p-3.5 text-left transition-all cursor-pointer ${
                isSelected
                  ? 'bg-white shadow-[0_2px_10px_rgba(15,23,42,0.08)]'
                  : 'bg-[#ECEEF2]/70 hover:bg-white/75 opacity-85 hover:opacity-100'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="inline-flex items-center gap-1.5 font-mono text-[12.5px] font-semibold text-[#111318] truncate">
                  <span className={`w-2 h-2 rounded-full shrink-0 ${toneStyle.dot}`} />
                  <span className="truncate">{topic.topicName}</span>
                </span>
                <span
                  className={`shrink-0 px-2 py-0.5 rounded-full text-[10.5px] font-semibold ${toneStyle.bg} ${toneStyle.text}`}
                >
                  {topic.structCountLabel}
                </span>
              </div>
              <div className="text-[12px] text-[#3C4043] mt-1 truncate">{topic.roleLabel}</div>
              <div className="flex items-center justify-between gap-2 mt-2 text-[11px] font-mono text-[#5F6368]">
                <span className="truncate">{topic.consumersLabel}</span>
                <span className="shrink-0">{topic.rateLabel}</span>
              </div>
            </button>
          );
        })}
      </div>

      {/* Auxiliary Topology Strip (DLQ + Preserved Mobile Consumer) */}
      {(inspector.dlqTopicName || inspector.preservedConsumerLabel) && (
        <div className="flex flex-wrap items-center gap-2 text-[11.5px]">
          {inspector.dlqTopicName && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white text-[#3C4043]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#16A34A]" />
              <span>DLQ prête :</span>
              <span className="font-mono font-medium text-[#111318]">{inspector.dlqTopicName}</span>
            </span>
          )}
          {inspector.preservedConsumerLabel && (
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white text-[#3C4043]">
              <span className="w-1.5 h-1.5 rounded-full bg-[#2563EB]" />
              <span>Consommateur actif conservé :</span>
              <span className="font-mono font-medium text-[#111318]">
                {inspector.preservedConsumerLabel}
              </span>
            </span>
          )}
        </div>
      )}

      {/* Sampled Message Explorer Card */}
      {activeSample && (
        <div className="rounded-xl bg-white p-4 shadow-[0_1px_3px_rgba(15,23,42,0.04)] space-y-3.5">
          {/* Sample Selector Pills + Timestamp */}
          <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-[#F1F3F5]">
            <div className="flex flex-wrap items-center gap-1.5">
              {samples.map((sample, sIdx) => {
                const isSampleActive = sIdx === safeSampleIdx;
                const sTone = TONE_SURFACE[sample.tone ?? 'neutral'];
                return (
                  <button
                    key={sample.id}
                    type="button"
                    onClick={() => setActiveSampleIdx(sIdx)}
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[12px] font-medium transition-colors cursor-pointer ${
                      isSampleActive
                        ? 'bg-[#1F2937] text-white'
                        : 'bg-[#F1F3F5] text-[#4B5563] hover:bg-[#E5E7EB]'
                    }`}
                  >
                    <span
                      className={`w-1.5 h-1.5 rounded-full ${
                        isSampleActive ? 'bg-white' : sTone.dot
                      }`}
                    />
                    <span>{sample.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="flex items-center gap-2 font-mono text-[11px] text-[#5F6368]">
              <span
                className={`px-2 py-0.5 rounded-full font-sans font-semibold text-[10.5px] ${
                  TONE_SURFACE[activeSample.tone ?? 'blue'].bg
                } ${TONE_SURFACE[activeSample.tone ?? 'blue'].text}`}
              >
                {activeSample.badge}
              </span>
              <span>{activeSample.publishTime}</span>
            </div>
          </div>

          {/* VIEW 1: Visual Nested STRUCT Blocks */}
          {viewMode === 'struct' ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2.5 select-text">
              {activeSample.groups.map((grp) => (
                <div key={grp.structName} className="rounded-xl bg-[#F7F8FA] p-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="px-1.5 py-0.5 rounded-md bg-[#E8EEF7] text-[#1D4ED8] font-mono text-[10px] font-semibold shrink-0">
                        STRUCT
                      </span>
                      <span className="font-mono text-[12.5px] font-semibold text-[#111318] truncate">
                        {grp.structName}
                      </span>
                    </div>
                    {grp.subtitle && (
                      <span className="text-[11px] text-[#5F6368] truncate">{grp.subtitle}</span>
                    )}
                  </div>

                  <div className="divide-y divide-[#ECEEF2]/80">
                    {grp.fields.map((f) => {
                      const fTone = f.tone ? TONE_SURFACE[f.tone] : null;
                      return (
                        <div
                          key={f.key}
                          className="py-1.5 first:pt-0.5 last:pb-0 flex items-center justify-between gap-2 text-[11.5px]"
                        >
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="font-mono text-[#5F6368] shrink-0">{f.key}</span>
                            <span className="font-mono text-[10px] text-[#9AA0A6] shrink-0">
                              {f.bqType}
                            </span>
                          </div>

                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="font-mono font-medium text-[#111318] truncate max-w-[185px]">
                              {f.value}
                            </span>
                            {f.tag && fTone && (
                              <span
                                className={`shrink-0 px-1.5 py-0.2 rounded-full text-[10px] font-semibold ${fTone.bg} ${fTone.text}`}
                              >
                                {f.tag}
                              </span>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            /* VIEW 2: Raw Decoded JSON Payload (1 opaque data JSON column) */
            <div className="space-y-2.5 select-text">
              <div className="rounded-xl bg-[#FFFBEB] px-3.5 py-2 text-[11.5px] text-[#92400E] leading-snug">
                <strong className="font-semibold">Piège du mode par défaut (`data JSON`) :</strong>{' '}
                tout le message est stocké dans <strong>une seule colonne opaque</strong> — BigQuery
                ne peut pas poser de Policy Tag CLS sur un sous-champ précis (ex :{' '}
                <code className="font-mono">debtor.iban</code>) sans masquer tout l&apos;événement.
              </div>
              <div className="rounded-xl bg-[#F5F6F8] px-4 py-3">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="font-mono text-[11.5px] text-[#5F6368]">
                    message.data (base64 decoded → colonne unique data JSON)
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyJson}
                    className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[11.5px] text-[#5F6368] hover:text-[#111318] hover:bg-[#E8EAED] transition-colors cursor-pointer"
                  >
                    {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                    <span>{copied ? 'Copié' : 'Copier'}</span>
                  </button>
                </div>
                <pre className="font-mono text-[12px] leading-[1.55] text-[#111318] overflow-x-auto">
                  <code>{activeSample.rawJson}</code>
                </pre>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Footer Takeaway */}
      {inspector.footerNote && (
        <div className="rounded-xl bg-[#EFF6FF] px-3.5 py-2.5 text-[12px] text-[#1E3A8A] leading-relaxed">
          {inspector.footerNote}
        </div>
      )}
    </div>
  );
};
