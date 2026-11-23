import dakSkillsData from './dakSkillsData.json';

export interface DakSkillSpec {
  id: string;
  name: string;
  filePath: string;
  description: string;
  markdown: string;
}

export interface DakMcpSpec {
  id: string;
  serverName: string;
  description: string;
  tools: string[];
}

export interface DakHookSpec {
  id: string;
  name: string;
  event: string;
  description: string;
}

export const DATA_AGENT_KIT_PLUGIN = {
  id: 'google-cloud-data-agent-kit',
  name: 'Data Agent Kit',
  publisher: 'Google Cloud',
  developer: 'Google LLC',
  version: '1.3.0',
  website: 'https://cloud.google.com/products/data-agent-kit',
  repository: 'https://github.com/GoogleCloudPlatform/data-agent-kit-plugin',
  shortDescription:
    "This plugin provides a specialized suite of skills for data engineers and database practitioners working on Google Cloud. It acts as an expert assistant, allowing you to use natural language prompts in your preferred coding agent to architect complex data pipelines, transform data with dbt, write Spark and BigQuery SQL notebooks, and orchestrate end-to-end workflows across GCP's data ecosystem.",
  heroPrompts: [
    'Create a PySpark notebook to train a distributed Random Forest model on the BigQuery table my_transactions',
    'Find datasets about customer orders in Knowledge Catalog and show their lineage',
    'My last Dataflow job failed. Find the root cause in the logs and propose a fix',
  ],
  mcpServers: [
    {
      id: 'bigquery',
      serverName: 'bigquery',
      description:
        'Execute SQL queries, inspect dataset and table metadata, search Knowledge Catalog, run forecasts, and analyze metric contributions.',
      tools: [
        'analyze_contribution',
        'ask_data_insights',
        'execute_sql',
        'forecast',
        'get_dataset_info',
        'get_table_info',
        'list_dataset_ids',
        'list_table_ids',
        'search_catalog',
      ],
    },
    {
      id: 'data-agent-kit',
      serverName: 'data-agent-kit',
      description:
        'Resolve active Google Cloud connections, read editor context, inspect resource templates, and render interactive charts.',
      tools: [
        'get_active_editor_context',
        'get_active_gcp_connection',
        'list_resource_templates',
        'read_resource',
        'render_chart',
      ],
    },
    {
      id: 'notebooks',
      serverName: 'notebooks',
      description:
        'Create, read, edit, and inspect Jupyter notebooks (.ipynb) across local Python and remote Spark/BigQuery kernels.',
      tools: [
        'create_notebook',
        'insert_markdown_cell',
        'insert_code_cell',
        'replace_cell',
        'delete_cell',
        'get_notebook_info',
        'read_cell',
        'list_cells',
        'search_cells',
        'get_cell_range',
        'get_cell_outputs',
      ],
    },
  ] as DakMcpSpec[],
  skills: dakSkillsData as DakSkillSpec[],
  hooks: [
    {
      id: 'datacloud-telemetry',
      name: 'googlecloudtools.datacloud_telemetry',
      event: 'PreToolUse / PostToolUse',
      description:
        'Automatically attaches Data Cloud attribution context to supported Google Cloud CLI and MCP operations while preserving least-privilege execution.',
    },
  ] as DakHookSpec[],
};

export const WORKSPACE_VISUAL_AUDIT_SKILL = {
  id: 'bq-visual-audit',
  name: 'bq-visual-audit',
  publisher: 'Workspace Skill · Banque Hexagone',
  filePath: '.agents/skills/bq-visual-audit/SKILL.md',
  shortDescription:
    'Déclenche automatiquement un contrôle visuel intégré (graphiques MCP data-agent-kit/render_chart, jauges Data Quality, ponts PNB et vignettes PDF ObjectRef) après chaque création de table, vue ou Data Product dans BigQuery.',
  triggers: [
    'Tables BigLake Managed Iceberg créées ou chargées via Dataproc Serverless Spark (raw_bank)',
    'Object Tables BigLake découvertes via Knowledge Catalog Cloud Storage Discovery (aperçu visuel des PDF)',
    'Modèles et Data Products dbt matérialisés en couche SILVER (scorecard Auto Data Quality)',
    'Vues gouvernées Knowledge Catalog en couche GOLD & tables prédictives BQML AI.FORECAST',
  ],
  mcpToolsUsed: ['bigquery/execute_sql', 'data-agent-kit/render_chart', 'bigquery/get_table_info'],
  skillMarkdownPreview: `---
name: bq-visual-audit
description: >-
  Exécute systématiquement un contrôle visuel post-création (graphiques ECharts via
  data-agent-kit/render_chart, jauges d'anomalies, ponts de réconciliation financière et
  aperçus documentaires ObjectRef) après toute création, alimentation ou exposition de table,
  table BigLake Managed Iceberg, Object Table, modèle dbt SILVER ou vue gouvernée GOLD dans BigQuery.
---

## Protocole obligatoire en 3 étapes
1. Requête SQL consolidée (volumes, complétude INFORMATION_SCHEMA, distribution métier, DQ).
2. Rendu graphique inline systématique via MCP \`data-agent-kit/render_chart\` (Apache ECharts V5).
3. Échantillonnage visuel de vignettes \`ObjectRef\` dès qu'une Object Table PDF est exposée.`,
};

