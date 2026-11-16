import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig, Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DEMO_CONFIG_YAML_PATH = path.resolve(__dirname, 'public/demo_config.yaml');

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

export default defineConfig({
  plugins: [demoConfigYamlPlugin(), react(), tailwindcss()],
});
