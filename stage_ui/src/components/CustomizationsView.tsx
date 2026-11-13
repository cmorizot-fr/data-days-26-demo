import React, { useState } from 'react';
import {
  Search,
  X,
  Plus,
  Check,
  Loader2,
  Sparkles,
  Server,
  ChevronDown,
  ChevronRight,
  ArrowRight,
  Cpu,
  GitBranch,
  Globe,
  TerminalSquare,
} from 'lucide-react';
import { DataAgentKitLogo } from './Icons';
import { DATA_AGENT_KIT_PLUGIN } from '../data/dakPlugin';

interface CustomizationsViewProps {
  installed: boolean;
  onInstall: () => void;
  onStartBuilding: () => void;
}

const OTHER_MARKETPLACE_PLUGINS = [
  {
    id: 'github-mcp',
    name: 'GitHub Enterprise MCP',
    description: 'Pull requests, issues, code search, and repository automation workflows.',
    icon: GitBranch,
    iconColor: 'text-[#111318]',
  },
  {
    id: 'cloud-run-kit',
    name: 'Cloud Run & Artifact Registry',
    description: 'Build, containerize, and deploy serverless microservices directly from Antigravity.',
    icon: TerminalSquare,
    iconColor: 'text-[#2563EB]',
  },
  {
    id: 'playwright-web',
    name: 'Browser & UI Verifier',
    description: 'Automated end-to-end visual inspection and interactive web testing skills.',
    icon: Globe,
    iconColor: 'text-[#059669]',
  },
];

export const CustomizationsView: React.FC<CustomizationsViewProps> = ({
  installed,
  onInstall,
  onStartBuilding,
}) => {
  const [tab, setTab] = useState<'marketplace' | 'installed'>('marketplace');
  const [query, setQuery] = useState('');
  const [installing, setInstalling] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleInstallClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (installed || installing) return;
    setInstalling(true);
    setTimeout(() => {
      setInstalling(false);
      setExpanded(true);
      onInstall();
    }, 1000);
  };

  const normalizedQuery = query.trim().toLowerCase();

  const matchesDak =
    normalizedQuery === '' ||
    'data agent kit bigquery biglake dbt knowledge catalog google cloud'
      .toLowerCase()
      .includes(normalizedQuery);

  const filteredOtherPlugins =
    tab === 'marketplace'
      ? OTHER_MARKETPLACE_PLUGINS.filter(
          (p) =>
            normalizedQuery === '' ||
            `${p.name} ${p.description}`.toLowerCase().includes(normalizedQuery)
        )
      : [];

  const showDakCard = tab === 'marketplace' ? matchesDak : installed && matchesDak;

  return (
    <div className="h-full overflow-y-auto px-10 py-10">
      <div className="max-w-3xl mx-auto">
        {/* Header matching Screenshot 3 */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-[22px] font-semibold tracking-tight text-[#111318]">
            Customizations
          </h1>

          {/* Segmented Marketplace / Installed pill using pure surface luminance */}
          <div className="flex items-center p-1 rounded-full bg-[#F1F3F6] text-[13px]">
            <button
              onClick={() => setTab('marketplace')}
              className={`px-3.5 py-1 rounded-full font-medium transition-all cursor-pointer ${
                tab === 'marketplace'
                  ? 'bg-white text-[#111318] shadow-[0_1px_4px_rgba(0,0,0,0.06)]'
                  : 'text-[#6B7280] hover:text-[#111318]'
              }`}
            >
              Marketplace
            </button>
            <button
              onClick={() => setTab('installed')}
              className={`px-3.5 py-1 rounded-full font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                tab === 'installed'
                  ? 'bg-white text-[#111318] shadow-[0_1px_4px_rgba(0,0,0,0.06)]'
                  : 'text-[#6B7280] hover:text-[#111318]'
              }`}
            >
              <span>Installed</span>
              {installed && (
                <span className="px-1.5 py-0.2 rounded-full text-[11px] bg-emerald-500/12 text-emerald-800 font-semibold">
                  1
                </span>
              )}
            </button>
          </div>
        </div>

        {/* Search input — empty by default */}
        <div className="relative mb-8">
          <Search className="w-4 h-4 text-[#6B7280] absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search marketplace plugins, skills, and MCP servers..."
            className="w-full bg-[#F3F4F7] hover:bg-[#ECEEF2] focus:bg-[#ECEEF2] transition-colors rounded-full pl-10 pr-10 py-2.5 text-[14px] text-[#111318] placeholder:text-[#8E939E] focus:outline-none"
          />
          {query && (
            <button
              onClick={() => setQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#8E939E] hover:text-[#111318] cursor-pointer"
              title="Clear search"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Results */}
        {showDakCard || filteredOtherPlugins.length > 0 ? (
          <div className="divide-y divide-[#ECEEF2]">
            {showDakCard && (
              <div className="py-3 first:pt-0">
                {/* Main Data Agent Kit Plugin Row (Screenshot 3 layout) */}
                <div
                  onClick={() => setExpanded(!expanded)}
                  className="group flex items-center justify-between p-4 rounded-2xl hover:bg-[#F7F8FA] transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-12 h-12 rounded-2xl bg-[#F7F8FA] group-hover:bg-white flex items-center justify-center shrink-0 transition-colors">
                      <DataAgentKitLogo className="w-9 h-9" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2.5">
                        <span className="text-[15px] font-semibold text-[#111318]">
                          {DATA_AGENT_KIT_PLUGIN.name}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#EEF2FF] text-[#1D4ED8]">
                          {DATA_AGENT_KIT_PLUGIN.version}
                        </span>
                        {installed && (
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/12 text-emerald-800">
                            Active on data-days-demo
                          </span>
                        )}
                      </div>
                      <p className="text-[13px] text-[#6B7280] truncate max-w-lg mt-0.5">
                        {DATA_AGENT_KIT_PLUGIN.shortDescription}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0 ml-4">
                    {installed ? (
                      <div className="flex items-center gap-2">
                        <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-500/12 text-emerald-800 text-[12px] font-medium">
                          <Check className="w-3.5 h-3.5" />
                          Installed
                        </span>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            onStartBuilding();
                          }}
                          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#111318] hover:bg-[#272B35] text-white text-[12px] font-medium transition-colors cursor-pointer"
                        >
                          <span>Open Chat</span>
                          <ArrowRight className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    ) : installing ? (
                      <span className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#F1F3F6] text-[#111318] text-[12px] font-medium">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Binding GCP MCP...
                      </span>
                    ) : (
                      <button
                        onClick={handleInstallClick}
                        className="w-9 h-9 rounded-full hover:bg-[#ECEEF2] flex items-center justify-center text-[#374151] transition-colors cursor-pointer"
                        title="Install Data Agent Kit"
                      >
                        <Plus className="w-5 h-5" />
                      </button>
                    )}

                    <div className="text-[#9CA3AF] pl-1">
                      {expanded ? (
                        <ChevronDown className="w-4 h-4" />
                      ) : (
                        <ChevronRight className="w-4 h-4" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded Architecture Drawer — Shows the audience what DAK brings */}
                {expanded && (
                  <div className="mt-2 mb-3 mx-2 p-6 rounded-2xl bg-[#F7F8FA] animate-fade-slide-up space-y-6">
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[12px] font-semibold uppercase tracking-wider text-[#6B7280]">
                          Ce que le Data Agent Kit active pour l'Agentic Data Cloud
                        </span>
                        <span className="text-[12px] font-mono text-[#4B5563]">
                          GCP: data-days-demo (europe-west1)
                        </span>
                      </div>
                      <p className="text-[13.5px] text-[#374151] leading-relaxed">
                        {DATA_AGENT_KIT_PLUGIN.fullDescription}
                      </p>
                    </div>

                    {/* 3 Native MCP Servers */}
                    <div>
                      <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[#111318] mb-3">
                        <Server className="w-3.5 h-3.5 text-[#2563EB]" />
                        <span>3 Serveurs MCP connectés à Google Cloud</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        {DATA_AGENT_KIT_PLUGIN.mcpServers.map((mcp) => (
                          <div key={mcp.id} className="p-3.5 rounded-xl bg-white space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="font-mono text-[12.5px] font-semibold text-[#111318]">
                                mcp:{mcp.serverName}
                              </span>
                              <span className="w-2 h-2 rounded-full bg-emerald-500" />
                            </div>
                            <p className="text-[11px] font-mono text-[#6B7280] truncate">
                              {mcp.endpoint}
                            </p>
                            <div className="flex flex-wrap gap-1 pt-1">
                              {mcp.tools.slice(0, 4).map((t) => (
                                <span
                                  key={t}
                                  className="px-2 py-0.5 rounded-md bg-[#F3F4F7] text-[10.5px] font-mono text-[#374151]"
                                >
                                  {t}
                                </span>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* 6 Specialized Skills */}
                    <div>
                      <div className="flex items-center gap-1.5 text-[12px] font-semibold text-[#111318] mb-3">
                        <Sparkles className="w-3.5 h-3.5 text-[#D97706]" />
                        <span>6 Skills spécialisés mobilisés dans les Démos 1, 2 & 3</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {DATA_AGENT_KIT_PLUGIN.skills.map((skill) => (
                          <div key={skill.id} className="p-3.5 rounded-xl bg-white space-y-1.5">
                            <div className="flex items-center justify-between gap-2">
                              <div className="flex items-center gap-1.5">
                                <Cpu className="w-3.5 h-3.5 text-[#4B5563]" />
                                <span className="font-mono text-[12.5px] font-semibold text-[#111318]">
                                  {skill.name}
                                </span>
                              </div>
                              <span className="px-2 py-0.5 rounded-full text-[10.5px] font-medium bg-[#EEF2FF] text-[#1D4ED8] shrink-0">
                                {skill.demoTag}
                              </span>
                            </div>
                            <p className="text-[12px] text-[#4B5563] leading-relaxed">
                              {skill.summary}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Additional Marketplace items visible when search is empty */}
            {filteredOtherPlugins.map((plugin) => {
              const IconComp = plugin.icon;
              return (
                <div
                  key={plugin.id}
                  className="py-3 flex items-center justify-between px-4 rounded-2xl hover:bg-[#F7F8FA] transition-colors"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-12 h-12 rounded-2xl bg-[#F7F8FA] flex items-center justify-center shrink-0">
                      <IconComp className={`w-5 h-5 ${plugin.iconColor}`} />
                    </div>
                    <div className="min-w-0">
                      <span className="text-[15px] font-semibold text-[#111318]">
                        {plugin.name}
                      </span>
                      <p className="text-[13px] text-[#6B7280] truncate max-w-lg mt-0.5">
                        {plugin.description}
                      </p>
                    </div>
                  </div>
                  <button
                    className="w-9 h-9 rounded-full hover:bg-[#ECEEF2] flex items-center justify-center text-[#374151] transition-colors cursor-pointer shrink-0"
                    title={`Install ${plugin.name}`}
                  >
                    <Plus className="w-5 h-5" />
                  </button>
                </div>
              );
            })}

            {/* Footer legal notice matching Screenshot 3 */}
            <div className="pt-6 text-[12px] text-[#6B7280] leading-relaxed">
              Google does not control the availability or functionality of third party developer
              tools. Your data from third party developer tools connected to your Antigravity
              instance may be shared with Google in accordance with the Google Privacy Policy.
            </div>
          </div>
        ) : (
          <div className="py-16 text-center rounded-2xl bg-[#F7F8FA]">
            <p className="text-[14px] text-[#6B7280]">
              {tab === 'installed' && !installed
                ? "Aucun plugin installé pour l'instant. Passez sur l'onglet Marketplace pour installer Data Agent Kit."
                : 'Aucun résultat pour cette recherche.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
