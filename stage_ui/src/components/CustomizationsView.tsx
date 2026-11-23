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
  BarChart3,
  Eye,
} from 'lucide-react';
import { DataAgentKitLogo } from './Icons';
import {
  AndroidCliIcon,
  AntigravitySdkIcon,
  ChromeDevToolsIcon,
  CloudRunIcon,
  DynatraceIcon,
  FirebaseIcon,
  GeminiApiIcon,
  GmailIcon,
  GoogleCalendarIcon,
  GoogleDocsIcon,
  GoogleDriveIcon,
  GoogleSheetsIcon,
  GoogleSlidesIcon,
  LinearIcon,
  NotionIcon,
  RoboticsIcon,
  StripeIcon,
  TealBracketIcon,
} from './MarketplaceIcons';
import {
  DATA_AGENT_KIT_PLUGIN,
  DakSkillSpec,
  WORKSPACE_VISUAL_AUDIT_SKILL,
} from '../data/dakPlugin';
import { SkillDetailModal } from './SkillDetailModal';
import { SelectedCustomizationId } from '../types';

interface CustomizationsViewProps {
  installed: boolean;
  selectedPlugin: SelectedCustomizationId;
  onSelectPlugin: (plugin: SelectedCustomizationId) => void;
  onInstall: () => void;
  onStartBuilding: () => void;
}

type DetailTab = 'overview' | 'skills' | 'mcp' | 'hooks';

interface MarketplacePluginItem {
  id: string;
  name: string;
  description: string;
  keywords: string;
  section: 'workspace' | 'build' | 'featured';
  icon: React.FC<{ className?: string }>;
  isDak?: boolean;
}

interface FeaturedTileSpec {
  id: string;
  name: string;
  description: string;
  icon: React.FC<{ className?: string }>;
  positionClass: string;
  iconClass: string;
}

const FEATURED_TILES: FeaturedTileSpec[] = [
  {
    id: 'firebase',
    name: 'Firebase',
    description:
      'Prototype, build, and run modern full-stack apps with Firestore, Auth, Hosting, and Cloud Functions via skills and MCP.',
    icon: FirebaseIcon,
    positionClass: 'left-[7%] top-[23%] -rotate-[6deg]',
    iconClass: 'w-7 h-7',
  },
  {
    id: 'notion',
    name: 'Notion',
    description:
      'Search pages, query databases, draft specs, and keep engineering documentation synchronized with your workspace.',
    icon: NotionIcon,
    positionClass: 'left-[22%] bottom-[14%] rotate-[3deg]',
    iconClass: 'w-7 h-7',
  },
  {
    id: 'context7',
    name: 'Context7',
    description:
      'Fetch up-to-date library documentation, API references, and versioned code examples directly into your coding session.',
    icon: TealBracketIcon,
    positionClass: 'left-[35%] top-[18%] -rotate-[2deg]',
    iconClass: 'w-7 h-7',
  },
  {
    id: 'linear',
    name: 'Linear',
    description:
      'Triage issues, link pull requests, inspect project roadmaps, and automate sprint workflows across engineering teams.',
    icon: LinearIcon,
    positionClass: 'left-[50%] bottom-[16%] rotate-[4deg]',
    iconClass: 'w-7 h-7',
  },
  {
    id: 'dynatrace',
    name: 'Dynatrace',
    description:
      'Investigate production issues with real Dynatrace data: problems and root causes, logs, metrics, traces, and vulnerabilities, via skills and the MCP...',
    icon: DynatraceIcon,
    positionClass: 'left-[64%] top-[15%]',
    iconClass: 'w-9 h-9',
  },
  {
    id: 'stripe',
    name: 'Stripe',
    description:
      'Inspect payments, subscriptions, webhooks, and billing APIs to build and test checkout integrations faster.',
    icon: StripeIcon,
    positionClass: 'right-[6%] bottom-[19%] rotate-[5deg]',
    iconClass: 'w-7 h-7',
  },
];

const GOOGLE_WORKSPACE_PLUGINS: MarketplacePluginItem[] = [
  {
    id: 'google-docs',
    name: 'Google Docs',
    description: 'Read, draft, and edit docs.',
    keywords: 'google workspace docs document text writing',
    section: 'workspace',
    icon: GoogleDocsIcon,
  },
  {
    id: 'google-sheets',
    name: 'Google Sheets',
    description: 'Read, write, and format spreadsheets.',
    keywords: 'google workspace sheets spreadsheets tables csv',
    section: 'workspace',
    icon: GoogleSheetsIcon,
  },
  {
    id: 'google-slides',
    name: 'Google Slides',
    description: 'Read, edit, and export presentations.',
    keywords: 'google workspace slides presentation deck',
    section: 'workspace',
    icon: GoogleSlidesIcon,
  },
  {
    id: 'google-drive',
    name: 'Google Drive',
    description: 'Search, upload, download, and share files.',
    keywords: 'google workspace drive files storage',
    section: 'workspace',
    icon: GoogleDriveIcon,
  },
  {
    id: 'google-calendar',
    name: 'Google Calendar',
    description: 'Check availability, schedule events, and RSVP.',
    keywords: 'google workspace calendar meetings schedule',
    section: 'workspace',
    icon: GoogleCalendarIcon,
  },
  {
    id: 'gmail',
    name: 'Gmail',
    description: 'Search, read, draft, and send emails in Gmail.',
    keywords: 'google workspace gmail email mail inbox',
    section: 'workspace',
    icon: GmailIcon,
  },
];

const BUILD_WITH_GOOGLE_PLUGINS: MarketplacePluginItem[] = [
  {
    id: 'gemini-api',
    name: 'Gemini API',
    description: 'Build applications and shell workflows with the Gemini API and SDKs.',
    keywords: 'google gemini api ai llm model',
    section: 'build',
    icon: GeminiApiIcon,
  },
  {
    id: 'chrome-devtools',
    name: 'Chrome DevTools',
    description: 'Reliable automation, in-depth debugging, and performance analysis.',
    keywords: 'google chrome devtools browser debug automation',
    section: 'build',
    icon: ChromeDevToolsIcon,
  },
  {
    id: 'android-cli',
    name: 'Android CLI',
    description: 'Core tools and knowledge required to develop and test Android apps.',
    keywords: 'google android cli mobile kotlin sdk',
    section: 'build',
    icon: AndroidCliIcon,
  },
  {
    id: 'firebase',
    name: 'Firebase',
    description: 'Prototype, build & run modern apps that users love with Firebase.',
    keywords: 'google firebase firestore auth hosting',
    section: 'build',
    icon: FirebaseIcon,
  },
  {
    id: 'robotics',
    name: 'Robotics',
    description: 'Simulate, control, and build intelligent robotics workflows.',
    keywords: 'google robotics simulation control',
    section: 'build',
    icon: RoboticsIcon,
  },
  {
    id: 'google-antigravity-sdk',
    name: 'Google Antigravity SDK',
    description: 'Build custom plugins, skills, and MCP servers for Antigravity.',
    keywords: 'google antigravity sdk plugin mcp skill',
    section: 'build',
    icon: AntigravitySdkIcon,
  },
  {
    id: 'data-agent-kit',
    name: DATA_AGENT_KIT_PLUGIN.name,
    description:
      'Connect your coding agent to 15+ Google Data Cloud services, including BigQuery, BigLake, Spark, AlloyDB, and Knowledge Catalog.',
    keywords:
      'data agent kit dak google cloud bigquery biglake dbt spark knowledge catalog alloydb sql pipeline analytics',
    section: 'build',
    icon: DataAgentKitLogo,
    isDak: true,
  },
  {
    id: 'cloud-run',
    name: 'Cloud Run',
    description: 'Build, containerize, and deploy serverless apps and APIs on Google Cloud.',
    keywords: 'google cloud run serverless containers deploy',
    section: 'build',
    icon: CloudRunIcon,
  },
];

const ALL_MARKETPLACE_ITEMS: MarketplacePluginItem[] = [
  ...BUILD_WITH_GOOGLE_PLUGINS.filter((item) => item.isDak),
  ...GOOGLE_WORKSPACE_PLUGINS,
  ...BUILD_WITH_GOOGLE_PLUGINS.filter((item) => !item.isDak),
  {
    id: 'dynatrace',
    name: 'Dynatrace',
    description:
      'Investigate production issues with real Dynatrace data: problems and root causes, logs, metrics, traces, and vulnerabilities, via skills and the MCP.',
    keywords: 'dynatrace observability monitoring logs traces metrics',
    section: 'featured',
    icon: DynatraceIcon,
  },
  {
    id: 'notion',
    name: 'Notion',
    description: 'Search pages, query databases, and draft engineering docs in Notion.',
    keywords: 'notion docs wiki knowledge base',
    section: 'featured',
    icon: NotionIcon,
  },
  {
    id: 'context7',
    name: 'Context7',
    description:
      'Fetch up-to-date library documentation, API references, and versioned code examples directly into your coding session.',
    keywords: 'context7 documentation docs library api reference',
    section: 'featured',
    icon: TealBracketIcon,
  },
  {
    id: 'linear',
    name: 'Linear',
    description: 'Triage issues, link pull requests, and manage sprints in Linear.',
    keywords: 'linear issues tracker project sprints',
    section: 'featured',
    icon: LinearIcon,
  },
  {
    id: 'stripe',
    name: 'Stripe',
    description: 'Inspect payments, subscriptions, and webhooks via Stripe tools.',
    keywords: 'stripe payments billing checkout',
    section: 'featured',
    icon: StripeIcon,
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
  const [activeFeaturedId, setActiveFeaturedId] = useState<string>('dynatrace');
  const [extraInstalledIds, setExtraInstalledIds] = useState<Record<string, boolean>>({});
  const [activeSkill, setActiveSkill] = useState<DakSkillSpec | null>(null);

  const triggerInstall = (e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    if (installed || installing) return;
    setInstalling(true);
    setTimeout(() => {
      setInstalling(false);
      onInstall();
    }, 850);
  };

  const toggleExtraInstall = (id: string, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setExtraInstalledIds((prev) => ({ ...prev, [id]: !prev[id] }));
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

          {/* TAB 2: SKILLS (Exact 32 official Data Agent Kit skills, click to inspect SKILL.md) */}
          {detailTab === 'skills' && (
            <div className="space-y-0.5">
              {DATA_AGENT_KIT_PLUGIN.skills.map((skill) => (
                <button
                  key={skill.id}
                  type="button"
                  onClick={() => setActiveSkill(skill)}
                  className="w-full flex items-baseline gap-3 py-[7px] px-2.5 -mx-2.5 rounded-lg hover:bg-[#F5F6F8] transition-colors text-left cursor-pointer group"
                >
                  <span className="text-[13.5px] font-medium text-[#1F1F1F] shrink-0">
                    /{skill.name}
                  </span>
                  <span className="text-[13.5px] text-[#5F6368] truncate min-w-0">
                    {skill.description}
                  </span>
                </button>
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

          {/* Metadata Footer: Developer / Version / Links (matches official plugin sheet) */}
          <div className="mt-10 pt-5 border-t border-[#ECEEF2] flex flex-wrap items-start justify-between gap-6 select-none">
            <div className="flex items-start gap-12">
              <div>
                <div className="text-[11.5px] text-[#5F6368]">Developer</div>
                <div className="text-[13px] font-semibold text-[#1F1F1F] mt-1">
                  {DATA_AGENT_KIT_PLUGIN.developer}
                </div>
              </div>
              <div>
                <div className="text-[11.5px] text-[#5F6368]">Version</div>
                <div className="text-[13px] font-semibold text-[#1F1F1F] mt-1">
                  {DATA_AGENT_KIT_PLUGIN.version}
                </div>
              </div>
            </div>

            <div>
              <div className="text-[11.5px] text-[#5F6368]">Links</div>
              <div className="flex items-center gap-4 mt-1">
                <a
                  href={DATA_AGENT_KIT_PLUGIN.website}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[13px] font-semibold text-[#1F1F1F] hover:text-[#1A73E8] transition-colors"
                >
                  <span>Website</span>
                  <ExternalLink className="w-3 h-3 text-[#5F6368]" />
                </a>
                <a
                  href={DATA_AGENT_KIT_PLUGIN.repository}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-[13px] font-semibold text-[#1F1F1F] hover:text-[#1A73E8] transition-colors"
                >
                  <span>Repository</span>
                  <ExternalLink className="w-3 h-3 text-[#5F6368]" />
                </a>
              </div>
            </div>
          </div>
        </div>

        <SkillDetailModal skill={activeSkill} onClose={() => setActiveSkill(null)} />
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
  // Marketplace / Installed View (Exact Antigravity Customizations UI)
  // =========================================================================
  const normalizedQuery = query.trim().toLowerCase();
  const queryTokens = normalizedQuery ? normalizedQuery.split(/\s+/).filter(Boolean) : [];
  const isSearching = queryTokens.length > 0;

  const matchesTokens = (haystack: string) =>
    queryTokens.length === 0 || queryTokens.every((token) => haystack.toLowerCase().includes(token));

  const activeFeatured =
    FEATURED_TILES.find((tile) => tile.id === activeFeaturedId) ?? FEATURED_TILES[4];
  const isFeaturedAdded = Boolean(extraInstalledIds[activeFeatured.id]);

  const searchResults = isSearching
    ? ALL_MARKETPLACE_ITEMS.filter((item) =>
        matchesTokens(`${item.name} ${item.description} ${item.keywords}`)
      )
    : [];

  const matchesVisualSkill = matchesTokens(
    `${WORKSPACE_VISUAL_AUDIT_SKILL.name} ${WORKSPACE_VISUAL_AUDIT_SKILL.shortDescription} visual check chart pdf preview bigquery render_chart audit skill`
  );

  const installedExtraItems = ALL_MARKETPLACE_ITEMS.filter(
    (item) => !item.isDak && Boolean(extraInstalledIds[item.id])
  );

  const renderGridItem = (item: MarketplacePluginItem) => {
    const IconComp = item.icon;
    const isItemAdded = item.isDak ? installed : Boolean(extraInstalledIds[item.id]);

    const handleRowClick = () => {
      if (item.isDak) {
        onSelectPlugin('dak');
      }
    };

    const handleAddClick = (e: React.MouseEvent) => {
      if (item.isDak) {
        triggerInstall(e);
      } else {
        toggleExtraInstall(item.id, e);
      }
    };

    return (
      <div
        key={item.id}
        onClick={handleRowClick}
        className={`group flex items-center justify-between gap-3 py-2.5 px-2.5 -mx-2.5 rounded-xl hover:bg-[#F7F8FA] transition-colors ${
          item.isDak ? 'cursor-pointer' : 'cursor-default'
        }`}
      >
        <div className="flex items-center gap-3.5 min-w-0">
          <div className="w-8 h-8 flex items-center justify-center shrink-0">
            <IconComp className="w-8 h-8" />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-[13.5px] font-semibold text-[#1F1F1F] leading-snug truncate">
                {item.name}
              </span>
              {item.isDak && installed && (
                <span className="px-2 py-0.5 rounded-full text-[10.5px] font-medium bg-[#E8F0FE] text-[#174EA6] shrink-0">
                  Added
                </span>
              )}
            </div>
            <p className="text-[12.5px] text-[#5F6368] leading-snug truncate mt-0.5">
              {item.description}
            </p>
          </div>
        </div>

        <div className="shrink-0">
          {item.isDak && installing ? (
            <span className="w-7 h-7 rounded-full bg-[#F1F3F5] flex items-center justify-center text-[#1B6EF3]">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            </span>
          ) : isItemAdded ? (
            <button
              type="button"
              onClick={item.isDak ? handleRowClick : handleAddClick}
              className="w-7 h-7 rounded-full bg-[#E8F0FE] text-[#174EA6] flex items-center justify-center transition-colors cursor-pointer"
              title={`${item.name} added`}
            >
              <Check className="w-4 h-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleAddClick}
              className="w-7 h-7 rounded-full hover:bg-[#E8EAED] text-[#5F6368] hover:text-[#1F1F1F] flex items-center justify-center transition-colors cursor-pointer"
              title={`Add ${item.name}`}
            >
              <Plus className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="h-full overflow-y-auto px-10 pt-7 pb-12 bg-white">
      <div className="max-w-[760px] mx-auto">
        {/* Header Row: Customizations + Marketplace | Installed */}
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-[20px] font-medium tracking-[-0.015em] text-[#1F1F1F]">
            Customizations
          </h1>

          {/* Segmented Marketplace / Installed pill using pure surface luminance */}
          <div className="inline-flex items-center p-[3px] rounded-full bg-[#F7F8FA] shadow-[0_1px_2px_rgba(15,23,42,0.06)] text-[12.5px]">
            <button
              type="button"
              onClick={() => setTab('marketplace')}
              className={`px-3.5 py-1 rounded-full font-medium transition-colors cursor-pointer ${
                tab === 'marketplace'
                  ? 'bg-[#E5E7EB] text-[#1F1F1F]'
                  : 'text-[#3C4043] hover:text-[#1F1F1F]'
              }`}
            >
              Marketplace
            </button>
            <button
              type="button"
              onClick={() => setTab('installed')}
              className={`px-3.5 py-1 rounded-full font-medium transition-colors cursor-pointer ${
                tab === 'installed'
                  ? 'bg-[#E5E7EB] text-[#1F1F1F]'
                  : 'text-[#3C4043] hover:text-[#1F1F1F]'
              }`}
            >
              Installed
            </button>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative mb-6">
          <Search className="w-3.5 h-3.5 text-[#80868B] absolute left-3.5 top-1/2 -translate-y-1/2 pointer-events-none" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Escape') setQuery('');
            }}
            placeholder="Search customizations..."
            className="w-full bg-[#EFEFF2] hover:bg-[#E8E9EE] focus:bg-[#E8E9EE] transition-colors rounded-full pl-9 pr-9 py-[7px] text-[13px] text-[#1F1F1F] placeholder:text-[#80868B] focus:outline-none"
          />
          {query && (
            <button
              type="button"
              onClick={() => setQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-[#80868B] hover:text-[#1F1F1F] cursor-pointer"
              title="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {/* ================================================================= */}
        {/* MODE 1: MARKETPLACE DEFAULT VIEW (No search query)                */}
        {/* ================================================================= */}
        {tab === 'marketplace' && !isSearching && (
          <div>
            {/* Featured Hero Banner Card (Pure surface luminance + neutral elevation, no colored border) */}
            <div className="rounded-[18px] overflow-hidden bg-white shadow-[0_1px_4px_rgba(15,23,42,0.06),0_6px_20px_rgba(15,23,42,0.04)] flex flex-col sm:flex-row min-h-[214px]">
              {/* Left Periwinkle-Lavender Floating Tiles Artwork */}
              <div
                className="sm:w-[58%] relative overflow-hidden min-h-[214px] select-none"
                style={{
                  background:
                    'radial-gradient(circle at 16% 24%, #D4DEFF 0%, transparent 56%), radial-gradient(circle at 84% 82%, #D1D8FF 0%, transparent 58%), linear-gradient(135deg, #E8EEFF 0%, #F1F4FF 52%, #DFE5FF 100%)',
                }}
              >
                {FEATURED_TILES.map((tile) => {
                  const TileIcon = tile.icon;
                  const isActive = tile.id === activeFeatured.id;
                  return (
                    <button
                      key={tile.id}
                      type="button"
                      onClick={() => setActiveFeaturedId(tile.id)}
                      title={tile.name}
                      className={`absolute ${tile.positionClass} flex items-center justify-center bg-white transition-all duration-200 cursor-pointer ${
                        isActive
                          ? 'w-[66px] h-[66px] rounded-[18px] shadow-[0_12px_28px_rgba(30,41,59,0.16)] scale-105 z-10'
                          : 'w-[54px] h-[54px] rounded-[16px] shadow-[0_8px_20px_rgba(30,41,59,0.09)] hover:scale-105 opacity-95'
                      }`}
                    >
                      <TileIcon className={isActive ? 'w-9 h-9' : tile.iconClass} />
                    </button>
                  );
                })}
              </div>

              {/* Right Featured Details Panel */}
              <div className="sm:w-[42%] bg-white px-7 py-6 flex flex-col justify-center">
                <span className="text-[11.5px] font-medium text-[#5F6368]">Featured</span>
                <h2 className="text-[18px] font-semibold text-[#1F1F1F] tracking-[-0.01em] mt-1">
                  {activeFeatured.name}
                </h2>
                <p className="text-[12.5px] leading-[1.52] text-[#5F6368] mt-2 line-clamp-3">
                  {activeFeatured.description}
                </p>

                <div className="mt-4 flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => toggleExtraInstall(activeFeatured.id)}
                    className={`inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-[12.5px] font-medium transition-colors cursor-pointer ${
                      isFeaturedAdded
                        ? 'bg-[#E8F0FE] text-[#174EA6]'
                        : 'bg-[#1B6EF3] hover:bg-[#1558D6] text-white'
                    }`}
                  >
                    {isFeaturedAdded ? (
                      <>
                        <Check className="w-3.5 h-3.5" />
                        <span>Added</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5" />
                        <span>Add</span>
                      </>
                    )}
                  </button>
                  <button
                    type="button"
                    onClick={() => setQuery(activeFeatured.name)}
                    className="px-3.5 py-1.5 rounded-full bg-[#EFEFF2] hover:bg-[#E4E6EB] text-[#1F1F1F] text-[12.5px] font-medium transition-colors cursor-pointer"
                  >
                    Details
                  </button>
                </div>
              </div>
            </div>

            {/* Section 1: Google Workspace */}
            <section className="mt-8">
              <h2 className="text-[14.5px] font-semibold text-[#1F1F1F]">Google Workspace</h2>
              <p className="text-[12px] text-[#5F6368] mt-0.5 mb-3.5">
                Connect to Google Workspace, including Docs, Sheets, Slides, Drive, Calendar, and
                Gmail.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-9 gap-y-1.5">
                {GOOGLE_WORKSPACE_PLUGINS.map(renderGridItem)}
              </div>
            </section>

            {/* Section 2: Build with Google */}
            <section className="mt-8">
              <h2 className="text-[14.5px] font-semibold text-[#1F1F1F]">Build with Google</h2>
              <p className="text-[12px] text-[#5F6368] mt-0.5 mb-3.5">
                Build on Google&apos;s developer platforms, including Android, Chrome, Gemini, and
                Google Cloud.
              </p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-x-9 gap-y-1.5">
                {BUILD_WITH_GOOGLE_PLUGINS.map(renderGridItem)}
              </div>
            </section>

            <div className="mt-10 pt-5 text-[11.5px] text-[#5F6368] leading-relaxed">
              Google does not control the availability or functionality of third party developer
              tools. Your data from third party developer tools connected to your Antigravity
              instance may be shared with Google in accordance with the Google Privacy Policy.
            </div>
          </div>
        )}

        {/* ================================================================= */}
        {/* MODE 2: MARKETPLACE SEARCH RESULTS (e.g. "data agent kit")        */}
        {/* ================================================================= */}
        {tab === 'marketplace' && isSearching && (
          <div>
            {searchResults.length > 0 || matchesVisualSkill ? (
              <div className="divide-y divide-[#ECEEF2]">
                {searchResults.map((item) => {
                  const IconComp = item.icon;
                  const isItemAdded = item.isDak ? installed : Boolean(extraInstalledIds[item.id]);

                  return (
                    <div key={item.id} className="py-2 first:pt-0">
                      <div
                        onClick={() => item.isDak && onSelectPlugin('dak')}
                        className={`group flex items-center justify-between p-3.5 rounded-2xl hover:bg-[#F7F8FA] transition-colors ${
                          item.isDak ? 'cursor-pointer' : 'cursor-default'
                        }`}
                      >
                        <div className="flex items-center gap-4 min-w-0">
                          <div className="w-11 h-11 rounded-2xl bg-[#F7F8FA] group-hover:bg-white flex items-center justify-center shrink-0 transition-colors">
                            <IconComp className="w-8 h-8" />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="text-[14.5px] font-semibold text-[#1F1F1F]">
                                {item.name}
                              </span>
                              {item.isDak && (
                                <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#F1F3F5] text-[#5F6368]">
                                  Google Cloud
                                </span>
                              )}
                              {isItemAdded && (
                                <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#E8F0FE] text-[#174EA6]">
                                  Added
                                </span>
                              )}
                            </div>
                            <p className="text-[13px] text-[#5F6368] line-clamp-2 mt-0.5 max-w-xl">
                              {item.isDak
                                ? DATA_AGENT_KIT_PLUGIN.shortDescription
                                : item.description}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0 ml-4">
                          {item.isDak && installing ? (
                            <span className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[#F1F3F6] text-[#1F1F1F] text-[12.5px] font-medium">
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              Adding
                            </span>
                          ) : isItemAdded ? (
                            <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#F1F3F5] text-[#3C4043] text-[12.5px] font-medium">
                              <Check className="w-3.5 h-3.5" />
                              Added
                            </span>
                          ) : (
                            <button
                              type="button"
                              onClick={(e) =>
                                item.isDak ? triggerInstall(e) : toggleExtraInstall(item.id, e)
                              }
                              className="w-9 h-9 rounded-full hover:bg-[#E8EAED] flex items-center justify-center text-[#3C4043] transition-colors cursor-pointer"
                              title={`Add ${item.name}`}
                            >
                              <Plus className="w-5 h-5" />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {matchesVisualSkill && (
                  <div className="py-2 first:pt-0">
                    <div
                      onClick={() => onSelectPlugin('bq-visual-audit')}
                      className="group flex items-center justify-between p-3.5 rounded-2xl hover:bg-[#F7F8FA] transition-colors cursor-pointer"
                    >
                      <div className="flex items-center gap-4 min-w-0">
                        <div className="w-11 h-11 rounded-2xl bg-[#E8F0FE] group-hover:bg-[#DBE8FE] flex items-center justify-center shrink-0 transition-colors">
                          <BarChart3 className="w-5 h-5 text-[#174EA6]" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-[14px] font-medium text-[#1F1F1F]">
                              {WORKSPACE_VISUAL_AUDIT_SKILL.name}
                            </span>
                            <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/12 text-emerald-900">
                              Workspace Skill
                            </span>
                          </div>
                          <p className="text-[13px] text-[#5F6368] truncate max-w-xl mt-0.5">
                            {WORKSPACE_VISUAL_AUDIT_SKILL.shortDescription}
                          </p>
                        </div>
                      </div>

                      <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#F1F3F5] text-[#3C4043] text-[12.5px] font-medium shrink-0 ml-4">
                        <Check className="w-3.5 h-3.5 text-[#188038]" />
                        Active
                      </span>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="py-16 text-center rounded-2xl bg-[#F8F9FA]">
                <p className="text-[14px] text-[#5F6368]">No matching customizations found.</p>
              </div>
            )}
          </div>
        )}

        {/* ================================================================= */}
        {/* MODE 3: INSTALLED TAB                                             */}
        {/* ================================================================= */}
        {tab === 'installed' && (
          <div className="divide-y divide-[#ECEEF2]">
            {installed &&
              matchesTokens(
                `${DATA_AGENT_KIT_PLUGIN.name} ${DATA_AGENT_KIT_PLUGIN.shortDescription} dak bigquery biglake`
              ) && (
                <div className="py-2 first:pt-0">
                  <div
                    onClick={() => onSelectPlugin('dak')}
                    className="group flex items-center justify-between p-3.5 rounded-2xl hover:bg-[#F7F8FA] transition-colors cursor-pointer"
                  >
                    <div className="flex items-center gap-4 min-w-0">
                      <div className="w-11 h-11 rounded-2xl bg-[#F7F8FA] group-hover:bg-white flex items-center justify-center shrink-0 transition-colors">
                        <DataAgentKitLogo className="w-8 h-8" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-[14.5px] font-semibold text-[#1F1F1F]">
                            {DATA_AGENT_KIT_PLUGIN.name}
                          </span>
                          <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-[#E8F0FE] text-[#174EA6]">
                            Added
                          </span>
                        </div>
                        <p className="text-[13px] text-[#5F6368] truncate max-w-xl mt-0.5">
                          {DATA_AGENT_KIT_PLUGIN.shortDescription}
                        </p>
                      </div>
                    </div>
                    <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#F1F3F5] text-[#3C4043] text-[12.5px] font-medium shrink-0 ml-4">
                      <Check className="w-3.5 h-3.5" />
                      Added
                    </span>
                  </div>
                </div>
              )}

            {matchesVisualSkill && (
              <div className="py-2 first:pt-0">
                <div
                  onClick={() => onSelectPlugin('bq-visual-audit')}
                  className="group flex items-center justify-between p-3.5 rounded-2xl hover:bg-[#F7F8FA] transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-4 min-w-0">
                    <div className="w-11 h-11 rounded-2xl bg-[#E8F0FE] group-hover:bg-[#DBE8FE] flex items-center justify-center shrink-0 transition-colors">
                      <BarChart3 className="w-5 h-5 text-[#174EA6]" />
                    </div>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-[14px] font-medium text-[#1F1F1F]">
                          {WORKSPACE_VISUAL_AUDIT_SKILL.name}
                        </span>
                        <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/12 text-emerald-900">
                          Workspace Skill
                        </span>
                      </div>
                      <p className="text-[13px] text-[#5F6368] truncate max-w-xl mt-0.5">
                        {WORKSPACE_VISUAL_AUDIT_SKILL.shortDescription}
                      </p>
                    </div>
                  </div>
                  <span className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#F1F3F5] text-[#3C4043] text-[12.5px] font-medium shrink-0 ml-4">
                    <Check className="w-3.5 h-3.5 text-[#188038]" />
                    Active
                  </span>
                </div>
              </div>
            )}

            {installedExtraItems
              .filter((item) => matchesTokens(`${item.name} ${item.description} ${item.keywords}`))
              .map((item) => {
                const IconComp = item.icon;
                return (
                  <div key={item.id} className="py-2">
                    <div className="flex items-center justify-between p-3.5 rounded-2xl hover:bg-[#F7F8FA] transition-colors">
                      <div className="flex items-center gap-4 min-w-0">
                        <div className="w-11 h-11 rounded-2xl bg-[#F7F8FA] flex items-center justify-center shrink-0">
                          <IconComp className="w-8 h-8" />
                        </div>
                        <div className="min-w-0">
                          <span className="text-[14.5px] font-semibold text-[#1F1F1F]">
                            {item.name}
                          </span>
                          <p className="text-[13px] text-[#5F6368] truncate max-w-xl mt-0.5">
                            {item.description}
                          </p>
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => toggleExtraInstall(item.id, e)}
                        className="inline-flex items-center gap-1 px-3 py-1.5 rounded-full bg-[#F1F3F5] hover:bg-[#E8EAED] text-[#3C4043] text-[12.5px] font-medium shrink-0 ml-4 cursor-pointer"
                      >
                        <Check className="w-3.5 h-3.5" />
                        Added
                      </button>
                    </div>
                  </div>
                );
              })}
          </div>
        )}
      </div>
    </div>
  );
};
