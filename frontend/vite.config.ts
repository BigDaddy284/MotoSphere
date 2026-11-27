import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'
import { engineFilesInDevelopment, engineFilesInTheSite } from './sitebuild/engineFiles.ts'
import { licences } from './sitebuild/licences.ts'
import { SITE_PATH } from './site.ts'

// https://vite.dev/config/
export default defineConfig({
  base: SITE_PATH,
  // The site is files and nothing else. Where an address names no file,
  // GitHub Pages answers "not found". Left to itself, Vite answers with the
  // page instead, in development and in the preview the browser tests use:
  // that is for an application that reads the address itself, which this one
  // does not. With this setting both answer as the published site does.
  appType: 'mpa',
  plugins: [react(), licences(), engineFilesInTheSite(), engineFilesInDevelopment()],
})
