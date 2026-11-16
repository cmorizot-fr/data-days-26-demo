/// <reference types="vite/client" />

declare module '*.yaml?raw' {
  const content: string;
  export default content;
}

declare module 'virtual:demo-config-yaml' {
  const content: string;
  export default content;
}
