/* 测试配置单独提供 UI 桩；生产构建的所有别名均指向真实源码。 */
import { fileURLToPath } from 'node:url';

import { defineConfig, mergeConfig } from 'vitest/config';

import base from './vite.config.ts';

const stub = (name: string) => fileURLToPath(new URL(`./test/stubs/${name}`, import.meta.url));
const source = (path: string) => fileURLToPath(new URL(`./src/${path}`, import.meta.url));

export default mergeConfig(base, defineConfig({
  resolve: {
    alias: {
      // 控制器与 React 组件的共享能力指向同一份 TS 源码。
      '@videodrome/legacy/core': source('core/index.ts'),
      '@videodrome/legacy/jav-title': source('core/jav-title.ts'),
      '@videodrome/legacy/tags': source('core/tags.ts'),
      '@videodrome/legacy/ui-sounds': source('ui-kit/sounds.ts'),
      '@videodrome/legacy/middle-truncate': source('ui-kit/middle-truncate.ts'),
      '@videodrome/legacy/ui': stub('legacy-ui.ts'),
      // 图片、外观、查询、历史与壳状态在控制器和页面之间保持模块身份。
      '@videodrome/card-art': source('card-art/index.ts'),
      '@videodrome/appearance': source('appearance/index.ts'),
      '@videodrome/query': source('query/index.ts'),
      '@videodrome/history': source('history/index.ts'),
      '@videodrome/shell': source('shell/index.ts'),
      '@/registry': source('react/evilcharts/registry'),
      '@/lib/utils': source('react/charts/cn.ts'),
      '@': source('react/boardui'),
    },
  },
  test: {
    environment: 'happy-dom',
    include: ['test/**/*.test.ts', 'test/**/*.test.tsx'],
    // 受限 runner 与本机资源守卫都给整棵测试进程树留固定预算；默认按 CPU 数扩张会耗尽进程槽。
    maxWorkers: 4,
    restoreMocks: true,
  },
}));
