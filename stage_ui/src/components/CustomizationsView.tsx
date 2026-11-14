import React, { useState } from 'react';
import {
  Search,
  X,
  Plus,
  Check,
  Copy,
  Loader2,
  ExternalLink,
  ArrowRight,
  GitBranch,
  Globe,
  TerminalSquare,
  BarChart3,
  Eye,
} from 'lucide-react';
import { DataAgentKitLogo } from './Icons';
import { DATA_AGENT_KIT_PLUGIN, WORKSPACE_VISUAL_AUDIT_SKILL } from '../data/dakPlugin';
import { SelectedCustomizationId } from '../types';

interface CustomizationsViewProps {
  installed: boolean;
  selectedPlugin: SelectedCustomizationId;
  onSelectPlugin: (plugin: SelectedCustomizationId) => void;
  onInstall: () => void;
  onStartBuilding: () => void;
}

type DetailTab = 'overview' | 'skills' | 'mcp' | 'hooks';

const OTHER_MARKETPLACE_PLUGINS = [
  {
    id: 'github-mcp',
    name: 'GitHub Enterprise MCP',
    description: 'Pull requests, issues, code search, and repository automation workflows.',
    icon: GitBranch,
    iconColor: 'text-[#1F1F1F]',
  },
  {
    id: 'cloud-run-kit',
    name: 'Cloud Run & Artifact Registry',
    description:
      'Build, containerize, and deploy serverless microservices directly from Antigravity.',
    icon: TerminalSquare,
    iconColor: 'text-[#1A73E8]',
  },
  {
    id: 'playwright-web',
    name: 'Browser & UI Verifier',
    description: 'Automated end-to-end visual inspection and interactive web testing skills.',
    icon: Globe,
    iconColor: 'text-[#188038]',
  },
];

const CodeSnippetBlock: React.FC<{ lang: string; code: string }> = ({ lang, code }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard?.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="rounded-xl bg-[#F5F6F8] px-4 py-3 my-2.5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[12.5px] text-[#5F6368] select-none">{lang}</span>
        <button
          type="button"
          onClick={handleCopy}
          className="p-1 rounded-md text-[#5F6368] hover:text-[#1F1F1F] hover:bg-[#E8EAED] transition-colors cursor-pointer"
          title="Copy to clipboard"
        >
          {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
        </button>
      </div>
      <pre className="font-mono text-[13px] text-[#1F1F1F] overflow-x-auto select-text">
        <code>{code}</code>
      </pre>
    </div>
  );
};

const InlineCode: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <code className="font-mono text-[12.5px] bg-[#F1F3F5] text-[#1F1F1F] px-1.5 py-0.5 rounded-md select-text">
    {children}
  </code>
);

const DocExternalLink: React.FC<{ href: string; children: React.ReactNode }> = ({
  href,
  children,
}) => (
  <a
    href={href}
    target="_blank"
    rel="noreferrer"
    className="inline-flex items-baseline gap-1 text-[#1A73E8] hover:underline"
  >
    <span>{children}</span>
    <ExternalLink className="w-3 h-3 inline self-center shrink-0" />
  </a>
);

export const CustomizationsView: React.FC<CustomizationsViewProps> = ({
  installed,
  selectedPlugin,
  onSelectPlugin,
  onInstall,
  onStartBuilding,
}) => {
  const [tab, setTab] = useState<'marketplace' | 'installed'>('marketplace');
  const [detailTab, setDetailTab] = useState<DetailTab>('overview');
  const [query, setQuery] = useState('');
  const [installing, setInstalling] = useState(false);

  const triggerInstall = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (installed || installing) return;
    setInstalling(true);
    setTimeout(() => {
      setInstalling(false);
      onInstall();
    }, 850);
  };

  // =========================================================================
  // Exact Data Agent Kit Sheet (matching Antigravity Plugin Detail View)
  // =========================================================================
  if (selectedPlugin === 'dak') {
    return (
      <div className="h-full overflow-y-auto px-10 py-10 bg-white select-text">
        <div className="max-w-[760px] mx-auto pb-12">
          {/* Header Row: Logo + Title + Add Button */}
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <DataAgentKitLogo className="w-10 h-10 shrink-0" />
              <h1 className="text-[22px] font-medium text-[#1F1F1F] tracking-[-0.01em]">
                {DATA_AGENT_KIT_PLUGIN.name}
              </h1>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              {installed ? (
                <>
                  <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#E8F0FE] text-[#174EA6] text-[13px] font-medium select-none">
                    <Check className="w-3.5 h-3.5" />
                    <span>Added</span>
                  </span>
                  <button
                    type="button"
                    onClick={onStartBuilding}
                    className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-[#1F1F1F] hover:bg-[#303134] text-white text-[13px] font-medium transition-colors cursor-pointer select-none"
                  >
                    <span>Open Chat</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </>
              ) : installing ? (
                <button
                  type="button"
                  disabled
                  className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-[#1B6EF3] text-white text-[13.5px] font-medium opacity-85 select-none"
                >
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Adding</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={triggerInstall}
                  className="px-4 py-1.5 rounded-full bg-[#1B6EF3] hover:bg-[#1558D6] text-white text-[13.5px] font-medium transition-colors cursor-pointer select-none"
                >
                  Add
                </button>
              )}
            </div>
          </div>

          {/* Intro Description */}
          <p className="mt-5 text-[14.5px] leading-[1.65] text-[#5F6368]">
            {DATA_AGENT_KIT_PLUGIN.shortDescription}
          </p>

          {/* 3 Hero Prompts Showcase Card (pure surface luminance, no colored border) */}
          <div className="mt-6 rounded-2xl bg-[#F8F9FA] px-5 py-4 space-y-3.5">
            {DATA_AGENT_KIT_PLUGIN.heroPrompts.map((promptText) => (
              <div key={promptText} className="flex items-center gap-3">
                <DataAgentKitLogo className="w-[18px] h-[18px] shrink-0" />
                <span className="text-[14px] text-[#1F1F1F] leading-snug">{promptText}</span>
              </div>
            ))}
          </div>

          {/* Sub-navigation Pills: Overview | Skills | MCP | Hooks */}
          <div className="mt-7 mb-7 flex items-center gap-1.5 select-none">
            {(
              [
                { id: 'overview', label: 'Overview' },
                { id: 'skills', label: 'Skills' },
                { id: 'mcp', label: 'MCP' },
                { id: 'hooks', label: 'Hooks' },
              ] as { id: DetailTab; label: string }[]
            ).map((item) => {
              const active = detailTab === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setDetailTab(item.id)}
                  className={`px-4 py-1.5 rounded-full text-[13.5px] font-medium transition-colors cursor-pointer ${
                    active
                      ? 'bg-[#EAECEF] text-[#1F1F1F]'
                      : 'text-[#5F6368] hover:text-[#1F1F1F] hover:bg-[#F3F4F6]'
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </div>

          {/* TAB 1: OVERVIEW (Exact replica of official Data Agent Kit sheet) */}
          {detailTab === 'overview' && (
            <div className="text-[14.5px] leading-[1.68] text-[#1F1F1F]">
              <h2 className="text-[20px] font-semibold text-[#1F1F1F] mb-3">Data Agent Kit</h2>
              <p className="mb-3.5">
                Data Agent Kit is a <strong className="font-semibold">free</strong> plugin that
                connects your coding agent to 15+ Google Data Cloud services, including BigQuery,
                Cloud Storage, Spanner, AlloyDB, Managed Service for Apache Spark, and Knowledge
                Catalog.
              </p>
              <p>
                Spend your time on insights, not boilerplate. Describe a data task in plain
                language, and watch your agent handle the heavy lifting for you: writing SQL
                queries, building notebooks, generating pipeline code, setting up ML workflows, and
                more.
              </p>

              <h3 className="text-[17px] font-semibold text-[#1F1F1F] mt-8 mb-3">Prerequisites</h3>
              <ul className="list-disc pl-5 space-y-2">
                <li>
                  <strong className="font-semibold">Node.js</strong> (latest LTS recommended).
                </li>
                <li>
                  <strong className="font-semibold">Google Cloud CLI</strong> (
                  <InlineCode>gcloud</InlineCode>), installed and authenticated:
                  <ol className="list-decimal pl-5 mt-2.5 space-y-3">
                    <li>
                      <DocExternalLink href="https://cloud.google.com/sdk/docs/install">
                        Install the gcloud CLI
                      </DocExternalLink>
                      .
                    </li>
                    <li>
                      <span>Log in with your Google Cloud account:</span>
                      <CodeSnippetBlock lang="bash" code="gcloud auth login" />
                    </li>
                    <li>
                      <span>
                        Log in to{' '}
                        <DocExternalLink href="https://cloud.google.com/docs/authentication/application-default-credentials">
                          Application Default Credentials (ADC)
                        </DocExternalLink>
                        :
                      </span>
                      <CodeSnippetBlock lang="bash" code="gcloud auth application-default login" />
                    </li>
                  </ol>
                </li>
              </ul>

              <h3 className="text-[17px] font-semibold text-[#1F1F1F] mt-8 mb-3">Configuration</h3>
              <p className="mb-3">
                Provide any prompt to your agent and it will walk you through configuring Data Agent
                Kit.
              </p>
              <p className="mb-2.5">
                Alternatively, you can manually invoke the Data Agent Kit setup skill:
              </p>
              <CodeSnippetBlock lang="text" code="/dak-setup" />
              <p className="mt-3">Restart your agent when prompted to complete the setup.</p>

              <h3 className="text-[17px] font-semibold text-[#1F1F1F] mt-8 mb-3">
                Features and Common Uses
              </h3>
              <ul className="list-disc pl-5 space-y-2.5">
                <li>
                  <strong className="font-semibold">Data engineering:</strong> Build pipelines that
                  turn source data into analysis-ready tables, with quality checks along the way.
                  Develop transformations with dbt or Dataform, schedule workflows with Managed
                  Service for Apache Airflow, and debug failed runs by tracing execution logs and
                  code.
                </li>
                <li>
                  <strong className="font-semibold">Data science:</strong> Develop experiments in
                  Jupyter notebooks on local Python or remote Managed Service for Apache Spark
                  kernels. Prepare features from BigQuery, train models with BigQuery ML, and
                  schedule batch inference.
                </li>
                <li>
                  <strong className="font-semibold">Data analysis:</strong> Explore data across
                  BigQuery, AlloyDB, and Cloud SQL. Find datasets with Knowledge Catalog, guided by
                  data quality metrics and lineage, then build visualizations or reusable data
                  models.
                </li>
              </ul>

              <h3 className="text-[17px] font-semibold text-[#1F1F1F] mt-8 mb-3">
                Example Prompts
              </h3>
              <ul className="list-disc pl-5 space-y-2">
                <li>
                  &quot;Create a PySpark notebook to train a distributed Random Forest model on the
                  BigQuery table <InlineCode>my_transactions</InlineCode>&quot;
                </li>
                <li>
                  &quot;Find datasets about customer orders in Knowledge Catalog and show their
                  lineage&quot;
                </li>
                <li>
                  &quot;Create an Airflow DAG that runs the dedup notebook, the dbt pipeline, and
                  model training every Monday morning&quot;
                </li>
                <li>
                  &quot;My last Dataflow job failed. Find the root cause in the logs and propose a
                  fix&quot;
                </li>
              </ul>

              <h3 className="text-[17px] font-semibold text-[#1F1F1F] mt-8 mb-3">
                Troubleshooting
              </h3>
              <p className="mb-3">
                If you see <InlineCode>could not find default credentials</InlineCode> or other auth
                errors, ensure you are logged into gcloud.
              </p>
              <p>
                Exit your agent, run <InlineCode>gcloud auth login</InlineCode> followed by{' '}
                <InlineCode>gcloud auth application-default login</InlineCode>, then restart your
                agent.
              </p>

              <h3 className="text-[17px] font-semibold text-[#1F1F1F] mt-8 mb-3">Security</h3>
              <p className="mb-3">
                Your agent can run tools and commands on your behalf. Apply the{' '}
                <strong className="font-semibold">principle of least privilege</strong> to every
                CLI, MCP server, and resource it can access:
              </p>
              <ul className="list-disc pl-5 space-y-2">
                <li>
                  Use{' '}
                  <DocExternalLink href="https://cloud.google.com/iam/docs/service-account-impersonation">
                    service account impersonation
                  </DocExternalLink>{' '}
                  instead of end-user credentials.
                </li>
                <li>
                  Grant the service account only the{' '}
                  <DocExternalLink href="https://cloud.google.com/iam/docs/understanding-roles">
                    roles it needs
                  </DocExternalLink>
                  .
                </li>
                <li>
                  Use{' '}
                  <DocExternalLink href="https://cloud.google.com/iam/docs/principal-access-boundary-policies">
                    Principal Access Boundary policies
                  </DocExternalLink>{' '}
                  with a condition in the policy binding to restrict your agent&apos;s service
                  accounts to only the projects and resources required for its tasks.
                </li>
              </ul>
            </div>
          )}

          {/* TAB 2: SKILLS */}
          {detailTab === 'skills' && (
            <div className="divide-y divide-[#ECEEF2]">
              {DATA_AGENT_KIT_PLUGIN.skills.map((skill) => (
                <div key={skill.id} className="py-3.5 first:pt-0">
                  <div className="font-mono text-[13.5px] font-medium text-[#1F1F1F]">
                    {skill.name}
                  </div>
                  <p className="mt-1 text-[13.5px] text-[#5F6368] leading-relaxed">
                    {skill.description}
                  </p>
                </div>
              ))}
            </div>
          )}

          {/* TAB 3: MCP */}
          {detailTab === 'mcp' && (
            <div className="divide-y divide-[#ECEEF2]">
              {DATA_AGENT_KIT_PLUGIN.mcpServers.map((mcp) => (
                <div key={mcp.id} className="py-4 first:pt-0 space-y-2">
                  <div className="font-mono text-[14px] font-medium text-[#1F1F1F]">
                    {mcp.serverName}
                  </div>
                  <p className="text-[13.5px] text-[#5F6368] leading-relaxed">{mcp.description}</p>
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {mcp.tools.map((toolName) => (
                      <span
                        key={toolName}
                        className="px-2.5 py-0.5 rounded-md bg-[#F3F4F6] font-mono text-[12px] text-[#3C4043]"
                      >
                        {toolName}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* TAB 4: HOOKS */}
          {detailTab === 'hooks' && (
            <div className="divide-y divide-[#ECEEF2]">
              {DATA_AGENT_KIT_PLUGIN.hooks.map((hook) => (
                <div key={hook.id} className="py-4 first:pt-0 space-y-1.5">
                  <div className="flex items-center gap-2.5">
                    <span className="font-mono text-[13.5px] font-medium text-[#1F1F1F]">
                      {hook.name}
                    </span>
                    <span className="px-2.5 py-0.5 rounded-full bg-[#F3F4F6] text-[11.5px] text-[#5F6368]">
                      {hook.event}
                    </span>
                  </div>
                  <p className="text-[13.5px] text-[#5F6368] leading-relaxed">{hook.description}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    );
  }

  // =========================================================================
  // Workspace Skill Sheet: bq-visual-audit (.agents/skills/bq-visual-audit/SKILL.md)
  // =========================================================================
  if (selectedPlugin === 'bq-visual-audit') {
    return (
      <div className="h-full overflow-y-auto px-10 py-10 bg-white select-text">
        <div className="max-w-[760px] mx-auto pb-12">
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3.5">
              <div className="w-11 h-11 rounded-2xl bg-[#E8F0FE] flex items-center justify-center shrink-0">
                <BarChart3 className="w-5 h-5 text-[#174EA6]" />
              </div>
              <div>
                <div className="flex items-center gap-2.5">
                  <h1 className="text-[22px] font-mono font-medium text-[#1F1F1F] tracking-[-0.01em]">
                    {WORKSPACE_VISUAL_AUDIT_SKILL.name}
                  </h1>
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/12 text-emerald-900 text-[11.5px] font-medium select-none">
                    Workspace Skill · Always Active
                  </span>
                </div>
                <p className="text-[12.5px] font-mono text-[#5F6368] mt-0.5">
                  {WORKSPACE_VISUAL_AUDIT_SKILL.filePath}
                </p>
              </div>
            </div>

            <button
              type="button"
              onClick={onStartBuilding}
              className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded-full bg-[#1F1F1F] hover:bg-[#303134] text-white text-[13px] font-medium transition-colors cursor-pointer select-none shrink-0"
            >
              <span>Retour au Chat</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          <p className="mt-5 text-[14.5px] leading-[1.65] text-[#5F6368]">
            {WORKSPACE_VISUAL_AUDIT_SKILL.shortDescription}
          </p>

          <div className="mt-6 rounded-2xl bg-[#F8F9FA] px-5 py-4 space-y-3">
            <div className="text-[12.5px] font-semibold uppercase tracking-wide text-[#5F6368]">
              Déclenchement automatique après chaque création dans BigQuery
            </div>
            {WORKSPACE_VISUAL_AUDIT_SKILL.triggers.map((trig) => (
              <div key={trig} className="flex items-center gap-3">
                <Eye className="w-4 h-4 text-[#1A73E8] shrink-0" />
                <span className="text-[13.5px] text-[#1F1F1F] leading-snug">{trig}</span>
              </div>
            ))}
          </div>

          <h3 className="text-[16px] font-semibold text-[#1F1F1F] mt-8 mb-2.5">
            Outils MCP Data Agent Kit orchestrés
          </h3>
          <div className="flex flex-wrap gap-2">
            {WORKSPACE_VISUAL_AUDIT_SKILL.mcpToolsUsed.map((tool) => (
              <span
                key={tool}
                className="px-3 py-1 rounded-lg bg-[#F1F3F5] font-mono text-[12.5px] text-[#202124]"
              >
                {tool}
              </span>
            ))}
          </div>

          <h3 className="text-[16px] font-semibold text-[#1F1F1F] mt-8 mb-2.5">
            Définition du Skill ({WORKSPACE_VISUAL_AUDIT_SKILL.filePath})
          </h3>
          <CodeSnippetBlock lang="markdown" code={WORKSPACE_VISUAL_AUDIT_SKILL.skillMarkdownPreview} />
        </div>
      </div>
    );
  }

  // =========================================================================
  // Marketplace / Installed List View
  // =========================================================================
  const normalizedQuery = query.trim().toLowerCase();

  const matchesDak =
    normalizedQuery === '' ||
    'data agent kit bigquery biglake dbt knowledge catalog google cloud spark'
      .toLowerCase()
      .includes(normalizedQuery);

  const matchesVisualSkill =
    normalizedQuery === '' ||
    'bq-visual-audit visual check chart pdf preview bigquery render_chart audit'
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
  const showVisualSkillCard = matchesVisualSkill;
  const installedCount = 1 + (installed ? 1 : 0);

  return (
    <div className="h-full overflow-y-auto px-10 py-10 bg-white">
      <div className="max-w-[760px] mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-[22px] font-medium tracking-[-0.01em] text-[#1F1F1F]">
            Customizations
          </h1>

          {/* Segmented Marketplace / Installed pill using surface luminance */}
          <div className="flex items-center p-1 rounded-full bg-[#F1F3F6] text-[13px]">
            <button
              type="button"
              onClick={() => setTab('marketplace')}
              className={`px-3.5 py-1 rounded-full font-medium transition-all cursor-pointer ${
                tab === 'marketplace'
                  ? 'bg-white text-[#1F1F1F] shadow-[0_1px_4px_rgba(0,0,0,0.06)]'
                  : 'text-[#5F6368] hover:text-[#1F1F1F]'
              }`}
            >
              Marketplace
            </button>
            <button
              type="button"
              onClick={() => setTab('installed')}
              className={`px-3.5 py-1 rounded-full font-medium transition-all cursor-pointer flex items-center gap-1.5 ${
                tab === 'installed'
                  ? 'bg-white text-[#1F1F1F] shadow-[0_1px_4px_rgba(0,0,0,0.06)]'
                  : 'text-[#5F6368] hover:text-[#1F1F1F]'
              }`}
            >
              <span>Installed</span>
              <span className="px-1.5 py-0.2 rounded-full text-[11px] bg-[#E8F0FE] text-[#174EA6] font-semibold">
                {installedCount}
              </span>
            </button>
          </div>
        </div>

        {/* Search input */}
        <div className="relative mb-8">
          <Search className="w-4 h-4 text-[#5F6368] absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search marketplace plugins, skills, and MCP servers..."
            className="w-full bg-[#F3F4F7] hover:bg-[#ECEEF2] focus:bg-[#ECEEF2] transition-colors rounded-full pl-10 pr-10 py-2.5 text-[14px] text-[#1F1F1F] placeholder:text-[#80868B] focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-3.5 top-1/2 -translate-y-1/2 text-[#80868B] hover:text-[#1F1F1F] cursor-pointer"
              title="Clear search"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Plugin & Workspace Skill List */}
        {showDakCard || showVisualSkillCard || filteredOtherPlugins.length > 0 ? (
          <div className="divide-y divide-[#ECEEF2]">
            {showDakCard && (
              <div className="py-2 first:pt-0">
                <div
                  onClick={() => onSelectPlugin('dak')}
                  className="group flex items-center justify-between p-4 rounded-2xl hover:bg-[#F8F9FA] transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-12 h-12 rounded-2xl bg-[#F8F9FA] group-hover:bg-white flex items-center justify-center shrink-0 transition-colors">
                      <DataAgentKitLogo className="w-9 h-9" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2.5">
                        <span className="text-[15px] font-medium text-[#1F1F1F]">
                          {DATA_AGENT_KIT_PLUGIN.name}
                        </span>
                        {installed && (
                          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-[#E8F0FE] text-[#174EA6]">
                            Added
                          </span>
                        )}
                      </div>
                      <p className="text-[13.5px] text-[#5F6368] truncate max-w-lg mt-0.5">
                        {DATA_AGENT_KIT_PLUGIN.shortDescription}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-4">
                    {installed ? (
                      <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#F1F3F5] text-[#3C4043] text-[12.5px] font-medium">
                        <Check className="w-3.5 h-3.5" />
                        Added
                      </span>
                    ) : installing ? (
                      <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#F1F3F6] text-[#1F1F1F] text-[12.5px] font-medium">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Adding
                      </span>
                    ) : (
                      <button
                        type="button"
                        onClick={triggerInstall}
                        className="w-9 h-9 rounded-full hover:bg-[#ECEEF2] flex items-center justify-center text-[#3C4043] transition-colors cursor-pointer"
                        title="Add Data Agent Kit"
                      >
                        <Plus className="w-5 h-5" />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )}

            {showVisualSkillCard && (
              <div className="py-2 first:pt-0">
                <div
                  onClick={() => onSelectPlugin('bq-visual-audit')}
                  className="group flex items-center justify-between p-4 rounded-2xl hover:bg-[#F8F9FA] transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-12 h-12 rounded-2xl bg-[#E8F0FE] group-hover:bg-[#DBE8FE] flex items-center justify-center shrink-0 transition-colors">
                      <BarChart3 className="w-5 h-5 text-[#174EA6]" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-[14.5px] font-medium text-[#1F1F1F]">
                          {WORKSPACE_VISUAL_AUDIT_SKILL.name}
                        </span>
                        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/12 text-emerald-900">
                          Workspace Skill
                        </span>
                      </div>
                      <p className="text-[13.5px] text-[#5F6368] truncate max-w-lg mt-0.5">
                        {WORKSPACE_VISUAL_AUDIT_SKILL.shortDescription}
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 shrink-0 ml-4">
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#F1F3F5] text-[#3C4043] text-[12.5px] font-medium">
                      <Check className="w-3.5 h-3.5 text-[#188038]" />
                      Active
                    </span>
                  </div>
                </div>
              </div>
            )}

            {filteredOtherPlugins.map((plugin) => {
              const IconComp = plugin.icon;
              return (
                <div key={plugin.id} className="py-2">
                  <div className="flex items-center justify-between p-4 rounded-2xl hover:bg-[#F8F9FA] transition-colors">
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-12 h-12 rounded-2xl bg-[#F8F9FA] flex items-center justify-center shrink-0">
                        <IconComp className={`w-5 h-5 ${plugin.iconColor}`} />
                      </div>
                      <div className="min-w-0">
                        <span className="text-[15px] font-medium text-[#1F1F1F]">
                          {plugin.name}
                        </span>
                        <p className="text-[13.5px] text-[#5F6368] truncate max-w-lg mt-0.5">
                          {plugin.description}
                        </p>
                      </div>
                    </div>
                    <button
                      type="button"
                      className="w-9 h-9 rounded-full hover:bg-[#ECEEF2] flex items-center justify-center text-[#3C4043] transition-colors cursor-pointer shrink-0"
                      title={`Add ${plugin.name}`}
                    >
                      <Plus className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              );
            })}

            <div className="pt-6 text-[12px] text-[#5F6368] leading-relaxed">
              Google does not control the availability or functionality of third party developer
              tools. Your data from third party developer tools connected to your Antigravity
              instance may be shared with Google in accordance with the Google Privacy Policy.
            </div>
          </div>
        ) : (
          <div className="py-16 text-center rounded-2xl bg-[#F8F9FA]">
            <p className="text-[14px] text-[#5F6368]">No matching customizations found.</p>
          </div>
        )}
      </div>
    </div>
  );
};
