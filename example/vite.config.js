import { resolve } from 'path'
import { defineConfig } from 'vite'

const outputDir = resolve(__dirname, 'build')

// https://vitejs.dev/config/
export default defineConfig({
    base: process.env.ASSET_PATH || '/static/',
    publicDir: false,
    build: {
        manifest: true,
        emptyOutDir: true,
        outDir: outputDir,
        sourcemap: true,
        rollupOptions: {
            input: {
                main: 'frontend/main.js',
            }
        }
    }
})
