import adapterNode from '@sveltejs/adapter-node';
import adapterVercel from '@sveltejs/adapter-vercel';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Two supported deploy targets, picked at build time -- neither disturbs the
// other:
//  - Docker / docker-compose / local `npm run build` (default): adapter-node,
//    a standalone Node server (see Dockerfile) -- `node build/index.js`.
//  - Vercel: Vercel's build environment sets VERCEL=1 automatically, which
//    switches this to adapter-vercel so `npm run build` emits the
//    `.vercel/output` the Vercel platform expects. See README's Cloud
//    Deployment section for the Render+Vercel split this enables.
const adapter = process.env.VERCEL ? adapterVercel() : adapterNode();

export default defineConfig({
	plugins: [
		sveltekit({
			compilerOptions: {
				// Force runes mode for the project, except for libraries. Can be removed in svelte 6.
				runes: ({ filename }) =>
					filename.split(/[/\\]/).includes('node_modules') ? undefined : true
			},
			adapter
		})
	]
});
