import { spawn } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import type { IncomingMessage, ServerResponse } from 'node:http';
import { defineConfig, Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, '..');
const DEMO_CONFIG_YAML_PATH = path.resolve(__dirname, 'public/demo_config.yaml');
const PYSPARK_SCRIPT_PATH = path.resolve(
  REPO_ROOT,
  '01_demo1_raw_aggregation/spark/parse_corebanking_iceberg.py'
);

function resolveGcloudBin(): { bin: string; extraPath: string } {
  const candidates = [
    process.env.GCLOUD_BIN,
    path.join(os.homedir(), 'google-cloud-sdk/bin/gcloud'),
    '/opt/homebrew/bin/gcloud',
    '/usr/local/bin/gcloud',
  ].filter((p): p is string => Boolean(p));
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      return { bin: candidate, extraPath: path.dirname(candidate) };
    }
  }
  return { bin: 'gcloud', extraPath: '' };
}

function loadRootEnv(): Record<string, string> {
  const envPath = path.resolve(REPO_ROOT, '.env');
  const out: Record<string, string> = {};
  if (!fs.existsSync(envPath)) return out;
  for (const rawLine of fs.readFileSync(envPath, 'utf8').split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const eq = line.indexOf('=');
    if (eq <= 0) continue;
    const k = line.slice(0, eq).trim();
    const v = line.slice(eq + 1).trim().replace(/^["']|["']$/g, '');
    out[k] = v;
  }
  return out;
}

function demoConfigYamlPlugin(): Plugin {
  const virtualId = 'virtual:demo-config-yaml';
  const resolvedId = '\0' + virtualId;

  return {
    name: 'demo-config-yaml-loader',
    resolveId(id) {
      if (id === virtualId) return resolvedId;
      return null;
    },
    load(id) {
      if (id === resolvedId) {
        this.addWatchFile(DEMO_CONFIG_YAML_PATH);
        const yamlText = fs.readFileSync(DEMO_CONFIG_YAML_PATH, 'utf8');
        return `export default ${JSON.stringify(yamlText)};`;
      }
      return null;
    },
    handleHotUpdate({ file, server }) {
      if (path.resolve(file) === DEMO_CONFIG_YAML_PATH) {
        const mod = server.moduleGraph.getModuleById(resolvedId);
        if (mod) {
          server.moduleGraph.invalidateModule(mod);
          return [mod];
        }
      }
    },
  };
}

function liveSparkTriggerPlugin(): Plugin {
  let lastTriggerAt = 0;
  let lastBatchId = '';
  let lastConsoleUrl = '';

  const handleRequest = (
    req: IncomingMessage,
    res: ServerResponse,
    next: () => void
  ) => {
    if (req.url !== '/api/trigger-spark-dryrun' || req.method !== 'POST') {
      next();
      return;
    }

    const now = Date.now();
    if (lastBatchId && now - lastTriggerAt < 20_000) {
      res.statusCode = 200;
      res.setHeader('Content-Type', 'application/json');
      res.end(
        JSON.stringify({
          status: 'debounced',
          batchId: lastBatchId,
          consoleUrl: lastConsoleUrl,
        })
      );
      return;
    }

    const envFile = loadRootEnv();
    const projectId = process.env.GCP_PROJECT_ID || envFile.GCP_PROJECT_ID || 'data-days-demo';
    const region = process.env.GCP_REGION || envFile.GCP_REGION || 'europe-west1';
    const datasetRaw = process.env.BQ_DATASET_RAW || envFile.BQ_DATASET_RAW || 'raw_bank';
    const bucketLanding =
      process.env.GCS_BUCKET_LANDING || envFile.GCS_BUCKET_LANDING || 'data-days-demo-landing';
    const subnetName = process.env.SPARK_SUBNET_NAME || envFile.SPARK_SUBNET_NAME || 'spark-sless-ew1';

    const d = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const stamp = `${d.getFullYear()}${pad(d.getMonth() + 1)}${pad(d.getDate())}-${pad(
      d.getHours()
    )}${pad(d.getMinutes())}${pad(d.getSeconds())}`;
    const batchId = `cbk-mainframe-live-${stamp}`;
    const consoleUrl = `https://console.cloud.google.com/dataproc/batches/${region}/${batchId}/monitoring?project=${projectId}`;

    lastTriggerAt = now;
    lastBatchId = batchId;
    lastConsoleUrl = consoleUrl;

    const gcloudArgs = [
      '--quiet',
      'dataproc',
      'batches',
      'submit',
      'pyspark',
      PYSPARK_SCRIPT_PATH,
      '--async',
      `--batch=${batchId}`,
      `--project=${projectId}`,
      `--region=${region}`,
      '--version=2.2',
      `--subnet=${subnetName}`,
      `--deps-bucket=gs://${bucketLanding}`,
      '--labels=datacloud=antigravity,domain=corebanking,mode=dryrun,env=demo2026',
      '--',
      '--project-id',
      projectId,
      '--dataset',
      datasetRaw,
      '--raw-gcs-uri',
      `gs://${bucketLanding}/RAW/corebanking`,
      '--temp-gcs-bucket',
      bucketLanding,
      '--dry-run',
    ];

    const prevMetrics = process.env.CLOUDSDK_METRICS_ENVIRONMENT;
    const metricsEnv = prevMetrics
      ? `${prevMetrics} datacloud.antigravity`
      : 'datacloud.antigravity';

    console.log(
      `\n[stage_ui] Soumission Dataproc Serverless (--dry-run, 0 écriture BQ) : ${batchId}`
    );
    console.log(`[stage_ui] Console : ${consoleUrl}`);

    const { bin: gcloudBin, extraPath } = resolveGcloudBin();
    const mergedPath = extraPath
      ? `${extraPath}:${process.env.PATH || '/usr/bin:/bin'}`
      : process.env.PATH;

    const child = spawn(gcloudBin, gcloudArgs, {
      cwd: REPO_ROOT,
      env: {
        ...process.env,
        PATH: mergedPath,
        CLOUDSDK_METRICS_ENVIRONMENT: metricsEnv,
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    child.stdout?.on('data', (chunk) => {
      process.stdout.write(`[spark-dryrun] ${chunk.toString()}`);
    });
    child.stderr?.on('data', (chunk) => {
      process.stderr.write(`[spark-dryrun] ${chunk.toString()}`);
    });
    child.on('exit', (code) => {
      if (code !== 0) {
        console.error(`[spark-dryrun] gcloud exited with code ${code}`);
      }
    });
    child.on('error', (err) => {
      console.error(`[spark-dryrun] Impossible de lancer gcloud : ${err.message}`);
    });

    res.statusCode = 200;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ status: 'submitted', batchId, consoleUrl }));
  };

  return {
    name: 'live-spark-trigger',
    configureServer(server) {
      server.middlewares.use(handleRequest);
    },
    configurePreviewServer(server) {
      server.middlewares.use(handleRequest);
    },
  };
}

export default defineConfig({
  plugins: [demoConfigYamlPlugin(), liveSparkTriggerPlugin(), react(), tailwindcss()],
});
