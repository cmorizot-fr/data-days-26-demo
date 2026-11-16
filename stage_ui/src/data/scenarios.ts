import { parse } from 'yaml';
import rawDemoConfigYaml from 'virtual:demo-config-yaml';
import { AnimationSpeed, DemoScenario, DemoWorkspace } from '../types';

export interface StageUiSettings {
  greetingName: string;
  defaultModel: string;
  defaultSpeed: AnimationSpeed;
  availableModels: string[];
  gcpConsoleUrl: string;
}

export interface ParsedDemoConfig {
  settings: StageUiSettings;
  workspaces: DemoWorkspace[];
  conversationsById: Record<string, DemoScenario>;
}

export function parseDemoConfigYaml(yamlText: string): ParsedDemoConfig {
  const parsed = parse(yamlText) as {
    settings?: Partial<StageUiSettings>;
    workspaces?: DemoWorkspace[];
  };

  const rawSpeed = parsed.settings?.defaultSpeed;
  const defaultSpeed: AnimationSpeed =
    rawSpeed === 'slow' || rawSpeed === 'normal' || rawSpeed === 'fast' ? rawSpeed : 'slow';

  const settings: StageUiSettings = {
    greetingName: parsed.settings?.greetingName ?? 'Clément',
    defaultModel: parsed.settings?.defaultModel ?? 'Gemini 4 - Carbon',
    defaultSpeed,
    availableModels: parsed.settings?.availableModels ?? [
      'Gemini 4 - Carbon',
      'Gemini 4 - Hydrogen',
      'Claude Sonnet 5.5',
    ],
    gcpConsoleUrl:
      parsed.settings?.gcpConsoleUrl ??
      'https://console.cloud.google.com/bigquery?project=data-days-demo',
  };

  const workspaces: DemoWorkspace[] = parsed.workspaces ?? [];
  const conversationsById: Record<string, DemoScenario> = Object.fromEntries(
    workspaces.flatMap((ws) => ws.conversations.map((conv) => [conv.id, conv]))
  );

  return { settings, workspaces, conversationsById };
}

/**
 * Configuration initiale chargée directement depuis `stage_ui/public/demo_config.yaml`
 * (supporte le Hot Module Replacement instantané sous `npm run dev`).
 */
export const INITIAL_DEMO_CONFIG: ParsedDemoConfig = parseDemoConfigYaml(rawDemoConfigYaml);

export const DEMO_SETTINGS: StageUiSettings = INITIAL_DEMO_CONFIG.settings;
export const DEMO_WORKSPACES: DemoWorkspace[] = INITIAL_DEMO_CONFIG.workspaces;
export const ALL_CONVERSATIONS: Record<string, DemoScenario> =
  INITIAL_DEMO_CONFIG.conversationsById;

/**
 * Recharge dynamiquement `./demo_config.yaml` au démarrage afin de permettre
 * l'édition à chaud même sur un build statique (`dist/demo_config.yaml`) par simple F5.
 */
export async function fetchRuntimeDemoConfig(): Promise<ParsedDemoConfig | null> {
  try {
    const res = await fetch('./demo_config.yaml', { cache: 'no-store' });
    if (!res.ok) return null;
    const text = await res.text();
    return parseDemoConfigYaml(text);
  } catch {
    return null;
  }
}
