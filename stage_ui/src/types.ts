export type DemoId = 'demo1' | 'demo2' | 'demo3' | 'demo4';

export type ActiveNav = 'chat' | 'customizations' | 'automations';

export type AnimationSpeed = 'slow' | 'normal' | 'fast';

export type FileIconKind = 'sql' | 'yml' | 'py' | 'dak' | 'cpy' | 'csv' | 'mp4' | 'md';

export type ExecutionStepTrace =
  | {
      id: string;
      action: 'ran';
      commandSummary: string;
      cwd?: string;
      command?: string;
      output?: string[];
      durationMs: number;
    }
  | {
      id: string;
      action: 'analyzed';
      icon: FileIconKind;
      fileName: string;
      lineRange?: string;
      durationMs: number;
    }
  | {
      id: string;
      action: 'edited';
      icon: FileIconKind;
      fileName: string;
      added: number;
      removed: number;
      durationMs: number;
    };

export interface FileDiffItem {
  path: string;
  language: 'sql' | 'yaml' | 'python' | 'markdown';
  badge: string;
  added: number;
  removed: number;
  content: string;
}

export interface ArtifactItem {
  id: string;
  title: string;
  subtitle: string;
  markdownSummary: {
    heading: string;
    metrics?: { label: string; value: string; tone?: 'neutral' | 'warning' | 'positive' | 'ruby' }[];
    bullets: string[];
    codeSnippet?: string;
  };
}

export interface SubagentItem {
  id: string;
  role: string;
  skill: string;
  status: 'completed' | 'running';
}

export interface BackgroundTaskItem {
  id: string;
  command: string;
  target: string;
  duration: string;
}

export interface InlineChip {
  kind: 'sql' | 'yml' | 'py' | 'bq' | 'kc' | 'mp4';
  label: string;
}

export interface EditorialSectionItem {
  title: string;
  chips?: InlineChip[];
  bullets: string[];
}

export type SelectedCustomizationId = 'dak' | 'bq-visual-audit' | null;

export type VisualTone = 'neutral' | 'positive' | 'warning' | 'ruby' | 'blue';

export interface VisualCheckKpi {
  label: string;
  value: string;
  sublabel?: string;
  tone?: VisualTone;
}

export interface VisualCheckBarRow {
  label: string;
  sublabel?: string;
  valueLabel: string;
  pct: number;
  tone?: VisualTone;
  badge?: string;
}

export interface VisualCheckDocPreview {
  id: string;
  title: string;
  subtitle: string;
  uri: string;
  metaBadge: string;
  highlightLabel: string;
  tone?: VisualTone;
  imageUrl: string;
}

export interface VisualCheckBlock {
  skillBadge?: string;
  title: string;
  subtitle?: string;
  kpis?: VisualCheckKpi[];
  chartTitle?: string;
  bars?: VisualCheckBarRow[];
  documentsTitle?: string;
  documents?: VisualCheckDocPreview[];
  footerNote?: string;
}

export interface PubSubPayloadField {
  key: string;
  value: string;
  bqType: string;
  tag?: string;
  tone?: VisualTone;
}

export interface PubSubPayloadGroup {
  structName: string;
  subtitle?: string;
  fields: PubSubPayloadField[];
}

export interface PubSubSampleMessage {
  id: string;
  label: string;
  badge: string;
  tone?: VisualTone;
  publishTime: string;
  rawJson: string;
  groups: PubSubPayloadGroup[];
}

export interface PubSubTopicQueueSpec {
  id: string;
  topicName: string;
  roleLabel: string;
  rateLabel: string;
  consumersLabel: string;
  structCountLabel: string;
  tone?: VisualTone;
  samples: PubSubSampleMessage[];
}

export interface PubSubInspectorBlock {
  title: string;
  subtitle?: string;
  dlqTopicName?: string;
  preservedConsumerLabel?: string;
  topics: PubSubTopicQueueSpec[];
  footerNote?: string;
}

export interface AskQuestionItem {
  id: string;
  question: string;
  isMultiSelect?: boolean;
  options: string[];
}

export interface InlineCodeBlock {
  label: string;
  language: string;
  code: string;
  resultTable?: string[];
  actionLink?: {
    label: string;
    url: string;
  };
}

export interface PromptTurn {
  id: string;
  chipLabel: string;
  prompt: string;
  promptAttachment?: VisualCheckDocPreview;
  workedDurationLabel: string;
  workGroupSummary: string;
  intermediateMessage: string;
  taskFinishedLabel: string;
  leadConfirmation: string;
  leadLink?: {
    text: string;
    url: string;
  };
  sectionHeading: string;
  items: EditorialSectionItem[];
  codeBlock?: InlineCodeBlock;
  pubsubInspector?: PubSubInspectorBlock;
  visualCheck?: VisualCheckBlock;
  askQuestions?: AskQuestionItem[];
  traces: ExecutionStepTrace[];
  filesChanged: FileDiffItem[];
  terminalLogs: string[];
  subagents: SubagentItem[];
  backgroundTasks: BackgroundTaskItem[];
  artifact?: ArtifactItem;
}

/**
 * Une conversation correspond à une étape précise d'une démo
 * à l'intérieur du Workspace de cette démo.
 */
export interface DemoScenario {
  id: string;
  demoId: DemoId;
  shortName: string;
  conversationTitle: string;
  projectFolder: string;
  gitBranch: string;
  greetingName: string;
  modelLabel: string;
  turns: PromptTurn[];
}

/**
 * Un Workspace dans la barre latérale correspond à une Démo complète
 * et regroupe les conversations de chacune de ses étapes.
 */
export interface DemoWorkspace {
  id: DemoId;
  workspaceLabel: string;
  folderName: string;
  conversations: DemoScenario[];
}
