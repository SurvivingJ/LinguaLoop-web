import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'happy-dom',
    setupFiles: ['./tests/unit/setup.js'],
    globals: true,
    coverage: {
      provider: 'v8',
      include: ['static/js/**'],
      exclude: ['static/js/admin-dashboard.js', 'static/js/listening_lab.js'],
    },
  },
});
