export interface DakSkillSpec {
  id: string;
  name: string;
  description: string;
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
  skills: [
    {
      id: 'accidental-data-loss-prevention',
      name: 'accidental-data-loss-prevention',
      description:
        'Requires explicit user consent before running commands or SQL statements that could cause irreversible data loss across SQL, Cloud Storage, or GCP infrastructure.',
    },
    {
      id: 'bigquery-ai-ml',
      name: 'bigquery-ai-ml',
      description:
        "Leverages BigQuery's built-in machine learning and GenAI capabilities for forecasting, anomaly detection, semantic search, multimodal extraction, and model evaluation.",
    },
    {
      id: 'bigquery-bigframes',
      name: 'bigquery-bigframes',
      description:
        'Generates Python code using BigQuery DataFrames (BigFrames) for scalable Python data processing, analysis, and machine learning.',
    },
    {
      id: 'bigquery-data-transfer-service',
      name: 'bigquery-data-transfer-service',
      description:
        'Discovers and inspects BigQuery Data Transfer Service (DTS) configurations and transfer metadata for ingestion pipelines.',
    },
    {
      id: 'bigquery-graph-author',
      name: 'bigquery-graph-author',
      description:
        'Authors BigQuery property graphs (CREATE PROPERTY GRAPH DDL) from relational tables, ER diagrams, or semantic models with relationship verification.',
    },
    {
      id: 'bigquery-graph-query',
      name: 'bigquery-graph-query',
      description:
        'Writes GQL (Graph Query Language) pattern matching, multi-hop traversals, GRAPH_TABLE SQL, and hybrid vector + graph queries on BigQuery.',
    },
    {
      id: 'bigquery-observability',
      name: 'bigquery-observability',
      description:
        'Retrieves BigQuery telemetry across INFORMATION_SCHEMA, Cloud Monitoring, and REST APIs for slot utilization, reservations, and job usage.',
    },
    {
      id: 'bigquery-optimization',
      name: 'bigquery-optimization',
      description:
        'Optimizes BigQuery capacity planning, storage layout (partitioning, clustering, billing models), materialized views, and SQL query performance.',
    },
    {
      id: 'bigquery-troubleshooting',
      name: 'bigquery-troubleshooting',
      description:
        'Performs step-by-step root-cause analysis on slow, failing, or expensive BigQuery jobs and execution plan bottlenecks.',
    },
    {
      id: 'building-data-apps',
      name: 'building-data-apps',
      description:
        'Builds modern interactive data dashboards and applications with React + Vite or Streamlit connected to Google Cloud data sources and Gemini Data Analytics.',
    },
    {
      id: 'cloud-databases-onboarding',
      name: 'cloud-databases-onboarding',
      description:
        'Guides database selection across Spanner, AlloyDB, Cloud SQL, and BigQuery based on workload requirements and assists with provisioning.',
    },
    {
      id: 'curate-context',
      name: 'curate-context',
      description:
        'Creates, validates, and publishes Knowledge Catalog (KC) context sets as Open Knowledge Format (OKF v0.2) bundles with kcmd.',
    },
    {
      id: 'data-autocleaning',
      name: 'data-autocleaning',
      description:
        'Applies automated data profiling, quality rules, schema mapping, and cleaning best practices for dbt, Dataform, and BigQuery pipelines.',
    },
    {
      id: 'dataform-bigquery',
      name: 'dataform-bigquery',
      description:
        'Generates and optimizes Dataform SQLX pipelines, source declarations, assertions, and workflow settings for BigQuery ELT.',
    },
    {
      id: 'dbt-bigquery',
      name: 'dbt-bigquery',
      description:
        'Expert guidance for creating, modifying, testing, and optimizing dbt models, sources, and incremental pipelines on BigQuery.',
    },
    {
      id: 'discover-assets',
      name: 'discover-assets',
      description:
        'Finds and inspects data assets, schemas, lineage, governance policies, and domain metadata across Google Cloud and Knowledge Catalog.',
    },
    {
      id: 'enforcing-resource-attribution',
      name: 'enforcing-resource-attribution',
      description:
        'Enforces telemetry attribution labels and metrics environment variables on gcloud and bq CLI invocations.',
    },
    {
      id: 'federate-lakehouse-catalog',
      name: 'federate-lakehouse-catalog',
      description:
        'Configures Google Cloud Lakehouse federated catalogs to remote Iceberg REST Catalogs (AWS Glue, Databricks Unity) and BigLake tables.',
    },
    {
      id: 'gcp-data-pipelines',
      name: 'gcp-data-pipelines',
      description:
        'Primary entry point for architecting, building, and orchestrating end-to-end GCP pipelines across dbt, Dataflow, Dataform, Managed Spark, DTS, and Cloud Composer.',
    },
    {
      id: 'gcp-dataflow',
      name: 'gcp-dataflow',
      description:
        'Guides writing, packaging, Flex Template deployment, and streaming performance diagnostics for Apache Beam pipelines on Dataflow.',
    },
    {
      id: 'gcp-managed-spark-upgrades',
      name: 'gcp-managed-spark-upgrades',
      description:
        'Assesses upgrade readiness and migrates Spark workloads on Google Cloud Managed Service for Apache Spark to newer runtime versions.',
    },
    {
      id: 'gcp-pipeline-orchestration',
      name: 'gcp-pipeline-orchestration',
      description:
        'Generates, deploys, and triggers Apache Airflow / Cloud Composer orchestration definitions across dbt, Spark, Dataform, and Vertex AI.',
    },
    {
      id: 'gcp-pipeline-resource-provisioning',
      name: 'gcp-pipeline-resource-provisioning',
      description:
        'Automates declarative environment-aware resource provisioning via deployment.yaml for BigQuery, Dataform, Dataproc, and DTS.',
    },
    {
      id: 'gcp-spark',
      name: 'gcp-spark',
      description:
        'Authors, optimizes, and runs PySpark and Spark SQL workloads on Managed Service for Apache Spark (Serverless, clusters, Spark Connect, and BigLake Iceberg).',
    },
    {
      id: 'gcp-spark-observability',
      name: 'gcp-spark-observability',
      description:
        'Monitors and audits Managed Spark clusters, serverless batches, DCU consumption, quotas, and Cloud Monitoring/Logging metrics.',
    },
    {
      id: 'gcp-spark-troubleshooting',
      name: 'gcp-spark-troubleshooting',
      description:
        'Diagnoses failed or slow Spark jobs, driver logs, compressed event logs, OOMs, and IAM/VPC issues on Dataproc and Serverless Spark.',
    },
    {
      id: 'managing-python-dependencies',
      name: 'managing-python-dependencies',
      description:
        'Enforces isolated virtual environments and project-level dependency managers (uv, poetry, venv) instead of global pip installs.',
    },
    {
      id: 'ml-best-practices',
      name: 'ml-best-practices',
      description:
        'Establishes rigorous methodology for data exploration, feature engineering, statistical testing, model evaluation, and BQML handoff.',
    },
    {
      id: 'notebook-guidance',
      name: 'notebook-guidance',
      description:
        'Guides structured Jupyter notebook authoring, cell-by-cell validation, %%bqsql magics, and reproducible visualizations.',
    },
    {
      id: 'schema-mapping',
      name: 'schema-mapping',
      description:
        'Analyzes source and target schemas to produce high-fidelity Mapping Manifestos before implementing multi-table ETL/ELT integrations.',
    },
  ] as DakSkillSpec[],
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
    'Object Tables BigLake découvertes via Dataplex Cloud Storage Discovery (aperçu visuel des PDF)',
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

