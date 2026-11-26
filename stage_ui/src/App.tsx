import React, { useEffect, useState } from 'react';
import {
  PanelLeft,
  ArrowLeft,
  ArrowRight,
  Search,
  Plus,
  Clock,
  Briefcase,
  Folder,
  FolderOpen,
  ChevronDown,
  ChevronRight,
  Settings,
  RotateCcw,
  Zap,
  PanelRight,
  MoreVertical,
  FileText,
  ExternalLink,
  ListFilter,
  FolderPlus,
} from 'lucide-react';
import { ActiveNav, AnimationSpeed, DemoId, PromptTurn, SelectedCustomizationId } from './types';
import {
  INITIAL_DEMO_CONFIG,
  ParsedDemoConfig,
  fetchRuntimeDemoConfig,
} from './data/scenarios';
import { CustomizationsView } from './components/CustomizationsView';
import { ChatStage, ExecutedTurn } from './components/ChatStage';
import {
  InspectorDrawer,
  InspectorModalState,
  OverviewPanel,
} from './components/OverviewPanel';

const SPEED_FACTORS: Record<AnimationSpeed, number> = {
  slow: 2.0,    // 2x moins vite (par défaut pour la scène)
  normal: 1.0,  // Vitesse nominale
  fast: 0.32,   // Mode accéléré pour répétitions
};

function scaleWorkedLabel(label: string, factor: number, extraSec = 0): string {
  return label.replace(
    /(\d+)s\b/,
    (_, sec) => `${Math.max(1, Math.round(Number(sec) * factor) + extraSec)}s`
  );
}

export const App: React.FC = () => {
  const [demoConfig, setDemoConfig] = useState<ParsedDemoConfig>(INITIAL_DEMO_CONFIG);
  const [activeConvId, setActiveConvId] = useState<string>(
    INITIAL_DEMO_CONFIG.workspaces[0]?.conversations[0]?.id ?? 'd1-step1'
  );
  const [expandedWorkspaces, setExpandedWorkspaces] = useState<Record<DemoId, boolean>>({
    demo1: true,
    demo2: true,
    demo3: true,
    demo4: false,
  });
  const [activeNav, setActiveNav] = useState<ActiveNav>('chat');
  const [selectedPlugin, setSelectedPlugin] = useState<SelectedCustomizationId>(null);
  const [dakInstalled, setDakInstalled] = useState<boolean>(false);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(true);
  const [overviewOpen, setOverviewOpen] = useState<boolean>(true);
  const [speedMode, setSpeedMode] = useState<AnimationSpeed>(
    INITIAL_DEMO_CONFIG.settings.defaultSpeed
  );
  const [speakerMenuOpen, setSpeakerMenuOpen] = useState<boolean>(false);
  const [inspectorModal, setInspectorModal] = useState<InspectorModalState>(null);

  const [historyByConv, setHistoryByConv] = useState<Record<string, ExecutedTurn[]>>({});
  const [isStreaming, setIsStreaming] = useState<boolean>(false);

  useEffect(() => {
    setDemoConfig(INITIAL_DEMO_CONFIG);
  }, []);

  useEffect(() => {
    fetchRuntimeDemoConfig().then((cfg) => {
      if (cfg && cfg.workspaces.length > 0) {
        setDemoConfig(cfg);
        setSpeedMode(cfg.settings.defaultSpeed);
      }
    });
  }, []);

  const currentScenario =
    demoConfig.conversationsById[activeConvId] || demoConfig.workspaces[0].conversations[0];
  const currentTurns = historyByConv[activeConvId] || [];

  const handleSendTurn = (turn: PromptTurn, customText?: string) => {
    if (isStreaming) return;
    const targetConvId = activeConvId;
    setIsStreaming(true);

    if (!dakInstalled) {
      setDakInstalled(true);
    }

    const speedFactor = SPEED_FACTORS[speedMode];
    const thinkingMs = speedMode === 'fast' ? 1600 : 5000;
    const scaledTurn: PromptTurn = {
      ...turn,
      workedDurationLabel: scaleWorkedLabel(
        turn.workedDurationLabel,
        speedFactor,
        Math.round(thinkingMs / 1000)
      ),
    };

    const initialEntry: ExecutedTurn = {
      turn: scaledTurn,
      userPromptText: customText || turn.prompt,
      status: 'thinking',
      visibleTraceCount: 0,
    };

    setHistoryByConv((prev) => ({
      ...prev,
      [targetConvId]: [
        ...(prev[targetConvId] || []).filter((t) => t.turn.id !== turn.id),
        initialEntry,
      ],
    }));

    // Real read-only Dataproc Serverless Spark trigger on Step 2 Turn 2 (0 BigQuery/Iceberg writes)
    if (turn.id === 'd1-s2-t2') {
      fetch('/api/trigger-spark-dryrun', { method: 'POST' })
        .then((res) => (res.ok ? res.json() : null))
        .then((data: { batchId?: string; consoleUrl?: string } | null) => {
          if (!data?.batchId || !data?.consoleUrl) return;
          const liveBatchId = data.batchId;
          const liveUrl = data.consoleUrl;
          setHistoryByConv((prev) => ({
            ...prev,
            [targetConvId]: (prev[targetConvId] || []).map((item) => {
              if (item.turn.id !== turn.id) return item;
              return {
                ...item,
                turn: {
                  ...item.turn,
                  leadLink: {
                    text: `console.cloud.google.com/dataproc/batches/europe-west1/${liveBatchId}`,
                    url: liveUrl,
                  },
                  traces: item.turn.traces.map((tr) =>
                    tr.action === 'ran' && tr.output
                      ? {
                          ...tr,
                          output: tr.output.map((line: string) =>
                            line.replace(/cbk-mainframe-iceberg-[0-9-]+/g, liveBatchId)
                          ),
                        }
                      : tr
                  ),
                },
              };
            }),
          }));
        })
        .catch(() => {
          // Graceful fallback when running offline or from static dist without Vite middleware
        });
    }

    // After 5s of "Working • •", start streaming the Work Tree traces
    setTimeout(() => {
      setHistoryByConv((prev) => ({
        ...prev,
        [targetConvId]: (prev[targetConvId] || []).map((item) =>
          item.turn.id === turn.id
            ? { ...item, status: 'streaming', visibleTraceCount: 1 }
            : item
        ),
      }));
    }, thinkingMs);

    let cumulativeMs = thinkingMs;

    turn.traces.forEach((tr, idx) => {
      if (idx === 0) return;
      cumulativeMs += tr.durationMs * speedFactor;
      setTimeout(() => {
        setHistoryByConv((prev) => ({
          ...prev,
          [targetConvId]: (prev[targetConvId] || []).map((item) =>
            item.turn.id === turn.id ? { ...item, visibleTraceCount: idx + 1 } : item
          ),
        }));
      }, cumulativeMs);
    });

    const totalMs =
      cumulativeMs + (turn.traces[turn.traces.length - 1]?.durationMs || 700) * speedFactor;

    setTimeout(() => {
      setHistoryByConv((prev) => ({
        ...prev,
        [targetConvId]: (prev[targetConvId] || []).map((item) =>
          item.turn.id === turn.id
            ? { ...item, status: 'done', visibleTraceCount: turn.traces.length }
            : item
        ),
      }));
      setIsStreaming(false);
    }, totalMs);
  };

  const handleResetCurrentConversation = () => {
    if (isStreaming) return;
    setHistoryByConv((prev) => ({ ...prev, [activeConvId]: [] }));
    setSpeakerMenuOpen(false);
  };

  const handleResetAllWorkspaces = () => {
    if (isStreaming) return;
    setHistoryByConv({});
    setSpeakerMenuOpen(false);
  };

  const handleNewConversation = () => {
    setActiveNav('chat');
    if (!isStreaming) {
      setHistoryByConv((prev) => ({ ...prev, [activeConvId]: [] }));
    }
  };

  const toggleWorkspace = (wsId: DemoId) => {
    setExpandedWorkspaces((prev) => ({ ...prev, [wsId]: !prev[wsId] }));
  };

  // Aggregate right-panel Overview data for current conversation step
  const completedTurns = currentTurns.filter((t) => t.status === 'done');
  const allFiles = completedTurns.flatMap((t) => t.turn.filesChanged);
  const allLogs = completedTurns.flatMap((t) => t.turn.terminalLogs);
  const allSubagents = currentTurns.flatMap((t) => t.turn.subagents);
  const allBgTasks = completedTurns.flatMap((t) => t.turn.backgroundTasks);
  const allArtifacts = completedTurns
    .map((t) => t.turn.artifact)
    .filter((a): a is NonNullable<typeof a> => Boolean(a));

  return (
    <div className="h-screen w-screen flex flex-col bg-[#F8F9FA] text-[#111318] select-none">
      {/* Top Window Chrome Bar matching Antigravity desktop header */}
      <header className="h-11 px-4 flex items-center justify-between shrink-0">
        {/* Left window controls + Breadcrumb */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 mr-2">
            <span className="w-3 h-3 rounded-full bg-[#FF5F57]" />
            <span className="w-3 h-3 rounded-full bg-[#FEBC2E]" />
            <span className="w-3 h-3 rounded-full bg-[#28C840]" />
          </div>

          <button
            type="button"
            onClick={() => setSidebarOpen(!sidebarOpen)}
            className="p-1.5 rounded-lg hover:bg-[#ECEEF2] text-[#5F6368] cursor-pointer"
            title="Toggle Sidebar"
          >
            <PanelLeft className="w-4 h-4" />
          </button>

          <div className="flex items-center gap-1 text-[#9AA0A6]">
            <button
              type="button"
              disabled={!(activeNav === 'customizations' && selectedPlugin !== null)}
              onClick={() => setSelectedPlugin(null)}
              className={`p-1 rounded-lg transition-colors ${
                activeNav === 'customizations' && selectedPlugin !== null
                  ? 'text-[#5F6368] hover:bg-[#ECEEF2] cursor-pointer'
                  : 'text-[#9AA0A6] cursor-default'
              }`}
              title="Back"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
            <span className="p-1">
              <ArrowRight className="w-4 h-4" />
            </span>
          </div>

          <Search className="w-4 h-4 text-[#5F6368] ml-1" />

          {/* Breadcrumb: Workspace Folder / Step Conversation */}
          {activeNav === 'chat' && (
            <div className="ml-4 flex items-center gap-2 text-[13.5px]">
              <span className="text-[#5F6368]">{currentScenario.projectFolder}</span>
              <span className="text-[#9AA0A6]">/</span>
              <span className="font-medium text-[#202124]">{currentScenario.shortName}</span>
            </div>
          )}
        </div>

        {/* Right Controls matching Antigravity: ⋮ + Open IDE + Artifacts/Overview toggles */}
        <div className="flex items-center gap-2 relative">
          <div className="relative">
            <button
              type="button"
              onClick={() => setSpeakerMenuOpen(!speakerMenuOpen)}
              className="p-1.5 rounded-full hover:bg-[#ECEEF2] text-[#5F6368] cursor-pointer"
              title="Options de démonstration"
            >
              <MoreVertical className="w-4 h-4" />
            </button>

            {speakerMenuOpen && (
              <div className="absolute right-0 top-full mt-1.5 w-64 p-1.5 rounded-2xl bg-white shadow-[0_10px_32px_rgba(15,23,42,0.12)] z-50 animate-fade-slide-up space-y-0.5">
                <div className="px-3 py-2 space-y-1.5">
                  <div className="flex items-center gap-2 text-[12.5px] text-[#5F6368]">
                    <Zap className="w-3.5 h-3.5 text-[#5F6368]" />
                    <span>Vitesse déroulé</span>
                  </div>
                  <div className="grid grid-cols-3 gap-1 p-1 rounded-xl bg-[#F1F3F5]">
                    {(
                      [
                        { id: 'slow', label: '0.5× (~10s)' },
                        { id: 'normal', label: '1× (~5s)' },
                        { id: 'fast', label: '3× (~1.5s)' },
                      ] as { id: AnimationSpeed; label: string }[]
                    ).map((opt) => {
                      const active = speedMode === opt.id;
                      return (
                        <button
                          key={opt.id}
                          type="button"
                          onClick={() => {
                            setSpeedMode(opt.id);
                            setSpeakerMenuOpen(false);
                          }}
                          className={`py-1 px-1.5 rounded-lg font-mono text-[11.5px] transition-colors cursor-pointer ${
                            active
                              ? 'bg-white text-[#111318] font-semibold'
                              : 'text-[#5F6368] hover:text-[#202124]'
                          }`}
                        >
                          {opt.label}
                        </button>
                      );
                    })}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleResetCurrentConversation}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-[#F8F9FA] text-[13px] text-[#202124] cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-[#5F6368]" />
                  <span>Réinitialiser cette étape</span>
                </button>

                <button
                  type="button"
                  onClick={handleResetAllWorkspaces}
                  className="w-full flex items-center gap-2 px-3 py-2 rounded-xl hover:bg-[#F8F9FA] text-[13px] text-[#202124] cursor-pointer"
                >
                  <RotateCcw className="w-3.5 h-3.5 text-[#5F6368]" />
                  <span>Tout réinitialiser (4 démos)</span>
                </button>

                <a
                  href={demoConfig.settings.gcpConsoleUrl}
                  target="_blank"
                  rel="noreferrer"
                  onClick={() => setSpeakerMenuOpen(false)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-[#F8F9FA] text-[13px] text-[#202124]"
                >
                  <span>Console BigQuery GCP</span>
                  <ExternalLink className="w-3.5 h-3.5 text-[#5F6368]" />
                </a>
              </div>
            )}
          </div>

          <a
            href={demoConfig.settings.gcpConsoleUrl}
            target="_blank"
            rel="noreferrer"
            className="px-3.5 py-1 rounded-full bg-[#F1F3F5] hover:bg-[#E4E7EB] text-[13px] font-medium text-[#202124] transition-colors"
          >
            Open IDE
          </a>

          {activeNav === 'chat' && currentTurns.length > 0 && (
            <div className="flex items-center gap-1 ml-0.5">
              <button
                type="button"
                onClick={() =>
                  allArtifacts.length > 0 &&
                  setInspectorModal({ kind: 'artifact', artifact: allArtifacts[0] })
                }
                className="p-1.5 rounded-lg hover:bg-[#ECEEF2] text-[#5F6368] cursor-pointer"
                title="Artifacts"
              >
                <FileText className="w-4 h-4" />
              </button>
              <button
                type="button"
                onClick={() => setOverviewOpen(!overviewOpen)}
                className={`p-1.5 rounded-lg transition-colors cursor-pointer ${
                  overviewOpen
                    ? 'bg-[#E8EAED] text-[#202124]'
                    : 'hover:bg-[#ECEEF2] text-[#5F6368]'
                }`}
                title="Toggle Overview"
              >
                <PanelRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </header>

      {/* Body Layout: Left Sidebar + Rounded White Main Surface */}
      <div className="flex-1 flex min-h-0">
        {sidebarOpen && (
          <aside className="w-[268px] shrink-0 px-3 pt-1 pb-3 flex flex-col justify-between overflow-y-auto">
            <div className="space-y-5">
              {/* Top Navigation */}
              <div className="space-y-1">
                <button
                  type="button"
                  onClick={handleNewConversation}
                  className="w-full flex items-center gap-2 px-3.5 py-2 rounded-xl bg-white hover:bg-[#FDFDFE] shadow-[0_1px_3px_rgba(0,0,0,0.04)] text-[13.5px] font-medium text-[#202124] transition-all cursor-pointer"
                >
                  <Plus className="w-4 h-4 text-[#5F6368]" />
                  <span>New Conversation</span>
                </button>

                <button
                  type="button"
                  onClick={() => setActiveNav('automations')}
                  className={`w-full flex items-center gap-2.5 px-3.5 py-2 rounded-xl text-[13.5px] transition-colors cursor-pointer ${
                    activeNav === 'automations'
                      ? 'bg-[#EAECEF] text-[#111318] font-medium'
                      : 'text-[#3C4043] hover:bg-[#EFEFF3]'
                  }`}
                >
                  <Clock className="w-4 h-4 text-[#5F6368]" />
                  <span>Automations</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setActiveNav('customizations');
                    setSelectedPlugin(null);
                  }}
                  className={`w-full flex items-center justify-between px-3.5 py-2 rounded-xl text-[13.5px] transition-colors cursor-pointer ${
                    activeNav === 'customizations'
                      ? 'bg-[#EAECEF] text-[#111318] font-medium'
                      : 'text-[#3C4043] hover:bg-[#EFEFF3]'
                  }`}
                >
                  <span className="flex items-center gap-2.5">
                    <Briefcase className="w-4 h-4 text-[#5F6368]" />
                    <span>Customizations</span>
                  </span>
                </button>
              </div>

              {/* Workspaces : 1 Workspace par Démo, et sous chaque Workspace : 1 Conversation par Étape */}
              <div className="px-0.5">
                <div className="flex items-center justify-between px-2.5 mb-2 text-[12px] text-[#70757A]">
                  <span>Workspaces</span>
                  <div className="flex items-center gap-2">
                    <ListFilter className="w-3.5 h-3.5" />
                    <FolderPlus className="w-3.5 h-3.5" />
                  </div>
                </div>

                <div className="space-y-2">
                  {demoConfig.workspaces.map((ws) => {
                    const isOpen = expandedWorkspaces[ws.id] ?? false;
                    const isActiveWs = currentScenario.demoId === ws.id && activeNav === 'chat';

                    return (
                      <div key={ws.id} className="space-y-0.5">
                        {/* Workspace Folder Header (1 per Demo) */}
                        <button
                          type="button"
                          onClick={() => toggleWorkspace(ws.id)}
                          title={ws.folderName}
                          className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-xl text-[13px] transition-colors cursor-pointer ${
                            isActiveWs
                              ? 'text-[#111318] font-medium hover:bg-[#EFEFF3]'
                              : 'text-[#3C4043] font-medium hover:bg-[#EFEFF3]'
                          }`}
                        >
                          <span className="flex items-center gap-2 min-w-0">
                            {isOpen ? (
                              <FolderOpen className="w-4 h-4 shrink-0 text-[#5F6368]" />
                            ) : (
                              <Folder className="w-4 h-4 shrink-0 text-[#5F6368]" />
                            )}
                            <span className="truncate">{ws.workspaceLabel}</span>
                          </span>
                          {isOpen ? (
                            <ChevronDown className="w-3.5 h-3.5 shrink-0 text-[#70757A]" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 shrink-0 text-[#70757A]" />
                          )}
                        </button>

                        {/* Step Conversations inside Workspace */}
                        {isOpen && (
                          <div className="pl-4 space-y-0.5">
                            {ws.conversations.map((conv) => {
                              const count = (historyByConv[conv.id] || []).length;
                              const selected = activeNav === 'chat' && activeConvId === conv.id;
                              return (
                                <button
                                  key={conv.id}
                                  type="button"
                                  onClick={() => {
                                    setActiveConvId(conv.id);
                                    setActiveNav('chat');
                                  }}
                                  className={`w-full flex items-center justify-between px-3 py-1.5 rounded-xl text-[12.5px] transition-colors cursor-pointer text-left ${
                                    selected
                                      ? 'bg-[#EAECEF] text-[#111318] font-medium'
                                      : 'text-[#4B5563] hover:bg-[#EFEFF3]'
                                  }`}
                                >
                                  <span className="truncate pr-1.5">{conv.shortName}</span>
                                  {count > 0 && (
                                    <span className="text-[11px] shrink-0 text-[#70757A]">now</span>
                                  )}
                                </button>
                              );
                            })}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Bottom Settings */}
            <div className="px-1 pt-3">
              <div className="flex items-center gap-2.5 px-3 py-1.5 text-[13.5px] text-[#3C4043]">
                <Settings className="w-4 h-4 text-[#5F6368]" />
                <span>Settings</span>
              </div>
            </div>
          </aside>
        )}

        {/* Main White Rounded Stage Surface */}
        <main className="flex-1 bg-white rounded-tl-2xl shadow-[0_0_24px_rgba(15,23,42,0.03)] flex min-w-0 overflow-hidden">
          {activeNav === 'customizations' && (
            <div className="flex-1 min-w-0">
              <CustomizationsView
                installed={dakInstalled}
                selectedPlugin={selectedPlugin}
                onSelectPlugin={setSelectedPlugin}
                onInstall={() => setDakInstalled(true)}
                onStartBuilding={() => setActiveNav('chat')}
              />
            </div>
          )}

          {activeNav === 'automations' && (
            <div className="flex-1 flex flex-col items-center justify-center p-12 text-center">
              <div className="max-w-md space-y-2">
                <h2 className="text-[18px] font-semibold text-[#111318]">Automations</h2>
                <p className="text-[13.5px] text-[#5F6368] leading-relaxed">
                  Les pipelines récurrents Auto Data Quality et la synchronisation{' '}
                  <span className="font-mono text-[#202124]">alloydb_sync</span> s'afficheront ici.
                </p>
              </div>
            </div>
          )}

          {activeNav === 'chat' && (
            <>
              <ChatStage
                scenario={currentScenario}
                executedTurns={currentTurns}
                dakInstalled={dakInstalled}
                isStreaming={isStreaming}
                overviewCollapsed={!overviewOpen && currentTurns.length > 0}
                onSendTurn={handleSendTurn}
                onOpenCustomizations={() => {
                  setSelectedPlugin('dak');
                  setActiveNav('customizations');
                }}
                onOpenVisualSkill={() => {
                  setSelectedPlugin('bq-visual-audit');
                  setActiveNav('customizations');
                }}
                onOpenInspector={setInspectorModal}
              />

              {currentTurns.length > 0 && (
                <OverviewPanel
                  files={allFiles}
                  terminalLogs={allLogs}
                  subagents={allSubagents}
                  backgroundTasks={allBgTasks}
                  artifacts={allArtifacts}
                  isStreaming={isStreaming}
                  collapsed={!overviewOpen}
                  onToggleCollapse={() => setOverviewOpen((prev) => !prev)}
                  onOpenInspector={setInspectorModal}
                  onOpenCustomizations={() => {
                    setSelectedPlugin('dak');
                    setActiveNav('customizations');
                  }}
                />
              )}
            </>
          )}
        </main>
      </div>

      {/* Slide-over Code / SQL / Terminal / Artifact Inspector */}
      <InspectorDrawer modal={inspectorModal} onClose={() => setInspectorModal(null)} />
    </div>
  );
};

export default App;
