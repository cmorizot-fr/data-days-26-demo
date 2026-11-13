export interface DakSkillSpec {
  id: string;
  name: string;
  category: 'Lakehouse & Ingestion' | 'Pipelines & Quality' | 'Semantics & Governance' | 'AI & Operational';
  demoTag: string;
  summary: string;
}

export interface DakMcpSpec {
  id: string;
  serverName: string;
  endpoint: string;
  tools: string[];
}

export const DATA_AGENT_KIT_PLUGIN = {
  id: 'google-cloud-data-agent-kit',
  name: 'Data Agent Kit',
  publisher: 'Google Cloud Data & AI',
  version: 'v2.4.0',
  shortDescription:
    'This plugin provides a specialized suite of skills and MCP servers for Google Agentic Data Cloud (BigQuery, BigLake, dbt, Knowledge Catalog & BQML).',
  fullDescription:
    "Équipe Antigravity d'une suite de Skills spécialisés et de connecteurs MCP natifs branchés sur votre environnement Google Cloud (`data-days-demo` · `europe-west1`) pour industrialiser l'ingénierie de données, la gouvernance sémantique et les agents analytiques sans copie inutile.",
  mcpServers: [
    {
      id: 'mcp-bq',
      serverName: 'bigquery',
      endpoint: 'projects/data-days-demo/locations/europe-west1',
      tools: [
        'execute_sql',
        'get_dataset_info',
        'get_table_info',
        'search_catalog',
        'forecast',
        'analyze_contribution',
      ],
    },
    {
      id: 'mcp-dak',
      serverName: 'data-agent-kit',
      endpoint: 'active-gcp-connection (ADC · europe-west1)',
      tools: [
        'get_active_gcp_connection',
        'get_active_editor_context',
        'read_resource',
        'render_chart',
      ],
    },
    {
      id: 'mcp-kc',
      serverName: 'knowledge-catalog',
      endpoint: 'dataplex.googleapis.com/v1 (OKF v0.2 / kcmd)',
      tools: [
        'publish_data_product',
        'run_auto_dq_scan',
        'curate_context_bundle',
        'sync_business_glossary',
      ],
    },
  ] as DakMcpSpec[],
  skills: [
    {
      id: 'federate-lakehouse-catalog',
      name: 'federate-lakehouse-catalog',
      category: 'Lakehouse & Ingestion',
      demoTag: 'Demo 1',
      summary:
        'Fédération Borderless Lakehouse (AWS Glue / S3 via BigQuery Omni), tables BigLake Iceberg managées et Object Tables GCS sans copie.',
    },
    {
      id: 'discover-assets',
      name: 'discover-assets',
      category: 'Lakehouse & Ingestion',
      demoTag: 'Demo 1',
      summary:
        'Inspection automatique des schémas multi-silos (CFONB Mainframe, ISO 20022, SAP/PCEC, PDF non structurés) et métadonnées techniques.',
    },
    {
      id: 'data-autocleaning',
      name: 'data-autocleaning',
      category: 'Pipelines & Quality',
      demoTag: 'Demo 2',
      summary:
        'Profilage statistique des tables RAW, détection des doublons/orphelins et génération des règles Auto Data Quality BigQuery.',
    },
    {
      id: 'dbt-bigquery',
      name: 'dbt-bigquery',
      category: 'Pipelines & Quality',
      demoTag: 'Demo 1 & 2',
      summary:
        'Génération industrielle des modèles dbt (staging → silver), tests schema.yml, partitionnement/clustering et publication Data Products.',
    },
    {
      id: 'curate-context',
      name: 'curate-context',
      category: 'Semantics & Governance',
      demoTag: 'Demo 3',
      summary:
        'Réconciliation des catalogues legacy, extraction multimodale (vidéos interviews .mp4) et publication des glossaires/contextes OKF dans Knowledge Catalog.',
    },
    {
      id: 'bigquery-ai-ml',
      name: 'bigquery-ai-ml',
      category: 'AI & Operational',
      demoTag: 'Demo 2 & 3',
      summary:
        'Extraction structurée de contrats PDF via AI.GENERATE, prévisions temporelles AI.FORECAST (TimesFM) et modèles de propension BQML.',
    },
  ] as DakSkillSpec[],
};
