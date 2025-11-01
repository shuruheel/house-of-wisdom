# Next.js 16 Release Announcement

**URL:** https://nextjs.org/blog/next-16  
**Date:** Tuesday, October 21st 2025

## Overview

Next.js 16 is now available with major improvements to Turbopack, caching, and the Next.js architecture.

## Key Features

### Cache Components

Cache Components are a new set of features designed to make caching in Next.js both more explicit and more flexible. They center around the new `"use cache"` directive, which can be used to cache pages, components, and functions, and which leverages the compiler to automatically generate cache keys wherever it's used.

**Key principles:**
- Caching is entirely **opt-in** by default
- All dynamic code in any page, layout, or API route is executed at **request time by default**
- Completes the story of **Partial Prerendering (PPR)**

**Enable in next.config.ts:**
```typescript
const nextConfig = {
  cacheComponents: true,
};

export default nextConfig;
```

**Note:** The previous `experimental.ppr` flag and configuration options have been removed in favor of the Cache Components configuration.

### Turbopack (stable)

Turbopack has reached stability for both development and production builds, and is now the **default bundler** for all new Next.js projects.

**Performance improvements:**
- **2–5× faster production builds**
- **Up to 10× faster Fast Refresh**

**Adoption:** More than 50% of development sessions and 20% of production builds on Next.js 15.3+ are already running on Turbopack.

**Opt-out to webpack:**
```bash
next dev --webpack
next build --webpack
```

### Turbopack File System Caching (beta)

Turbopack now supports filesystem caching in development, storing compiler artifacts on disk between runs for significantly faster compile times across restarts, especially in large projects.

**Enable in configuration:**
```typescript
const nextConfig = {
  experimental: {
    turbopackFileSystemCacheForDev: true,
  },
};

export default nextConfig;
```

### Next.js Devtools MCP

Next.js 16 introduces Next.js DevTools MCP, a Model Context Protocol integration for AI-assisted debugging with contextual insight into your application.

**Features:**
- Next.js knowledge: Routing, caching, and rendering behavior
- Unified logs: Browser and server logs without switching contexts
- Automatic error access: Detailed stack traces without manual copying
- Page awareness: Contextual understanding of the active route

### proxy.ts (formerly middleware.ts)

`proxy.ts` replaces `middleware.ts` and makes the app's network boundary explicit. `proxy.ts` runs on the Node.js runtime.

**Migration:**
```typescript
// proxy.ts
export default function proxy(request: NextRequest) {
  return NextResponse.redirect(new URL('/home', request.url));
}
```

**What to do:** Rename `middleware.ts` → `proxy.ts` and rename the exported function to `proxy`. Logic stays the same.

**Note:** The `middleware.ts` file is still available for Edge runtime use cases, but it is deprecated and will be removed in a future version.

### Logging Improvements

Development request logs now show where time is spent:
- **Compile:** Routing and compilation
- **Render:** Running your code and React rendering

Build process now shows detailed timing:
```
   ▲ Next.js 16 (Turbopack)
 
 ✓ Compiled successfully in 615ms
 ✓ Finished TypeScript in 1114ms
 ✓ Collecting page data in 208ms
 ✓ Generating static pages in 239ms
 ✓ Finalizing page optimization in 5ms
```

## Enhanced Routing and Navigation

Complete overhaul of the routing and navigation system for leaner and faster page transitions.

### Layout deduplication
When prefetching multiple URLs with a shared layout, the layout is downloaded once instead of separately for each Link. For example, a page with 50 product links now downloads the shared layout once instead of 50 times.

### Incremental prefetching
Next.js only prefetches parts not already in cache, rather than entire pages. The prefetch cache now:
- Cancels requests when the link leaves the viewport
- Prioritizes link prefetching on hover or when re-entering the viewport
- Re-prefetches links when their data is invalidated
- Works seamlessly with Cache Components

## Improved Caching APIs

### revalidateTag() (updated)

Now requires a `cacheLife` profile as the second argument to enable stale-while-revalidate (SWR) behavior:

```typescript
import { revalidateTag } from 'next/cache';

// ✅ Use built-in cacheLife profile (we recommend 'max' for most cases)
revalidateTag('blog-posts', 'max');

// Or use other built-in profiles
revalidateTag('news-feed', 'hours');
revalidateTag('analytics', 'days');

// Or use an inline object with a custom revalidation time
revalidateTag('products', { revalidate: 3600 });

// ⚠️ Deprecated - single argument form
revalidateTag('blog-posts');
```

Use `revalidateTag()` when you want to invalidate only properly tagged cached entries with stale-while-revalidate behavior. This is ideal for static content that can tolerate eventual consistency.

### updateTag() (new)

New Server Actions-only API that provides read-your-writes semantics, expiring and immediately reading fresh data within the same request:

```typescript
'use server';

import { updateTag } from 'next/cache';

export async function updateUserProfile(userId: string, profile: Profile) {
  await db.users.update(userId, profile);
  
  // Expire cache and refresh immediately - user sees their changes right away
  updateTag(`user-${userId}`);
}
```

This ensures interactive features reflect changes immediately. Perfect for forms, user settings, and any workflow where users expect to see their updates instantly.

### refresh() (new)

New Server Actions-only API for refreshing uncached data only. It doesn't touch the cache at all:

```typescript
'use server';

import { refresh } from 'next/cache';

export async function markNotificationAsRead(notificationId: string) {
  await db.notifications.markAsRead(notificationId);
  
  // Refresh the notification count displayed in the header
  refresh();
}
```

## React Compiler Support (stable)

Built-in support for the React Compiler is now stable in Next.js 16. The React Compiler automatically memoizes components, reducing unnecessary re-renders with zero manual code changes.

```typescript
const nextConfig = {
  reactCompiler: true,
};

export default nextConfig;
```

**Note:** Not enabled by default as compile times in development and during builds will be higher when enabling this option.

```bash
npm install babel-plugin-react-compiler@latest
```

## Build Adapters API (alpha)

Build Adapters allow you to create custom adapters that hook into the build process, enabling deployment platforms and custom build integrations to modify Next.js configuration or process build output.

```javascript
const nextConfig = {
  experimental: {
    adapterPath: require.resolve('./my-adapter.js'),
  },
};

module.exports = nextConfig;
```

## React 19.2 and Canary Features

The App Router in Next.js 16 uses the latest React Canary release, which includes React 19.2 features:

- **View Transitions:** Animate elements that update inside a Transition or navigation
- **useEffectEvent:** Extract non-reactive logic from Effects into reusable Effect Event functions
- **Activity:** Render "background activity" by hiding UI with display: none while maintaining state

## Breaking Changes

### Version Requirements

| Change | Details |
|--------|---------|
| Node.js 20.9+ | Minimum version now 20.9.0 (LTS); Node.js 18 no longer supported |
| TypeScript 5+ | Minimum version now 5.1.0 |
| Browsers | Chrome 111+, Edge 111+, Firefox 111+, Safari 16.4+ |

### Removals

- **AMP support** - All AMP APIs and configs removed
- **next lint command** - Use Biome or ESLint directly; `next build` no longer runs linting
- **experimental.ppr flag** - Removed; evolving into Cache Components
- **Sync params, searchParams props access** - Must use async: `await params`, `await searchParams`
- **Sync cookies(), headers(), draftMode() access** - Must use async: `await cookies()`, `await headers()`, `await draftMode()`

### Behavior Changes

| Changed Behavior | Details |
|------------------|---------|
| Default bundler | Turbopack is now the default bundler for all apps |
| images.minimumCacheTTL default | Changed from 60s to 4 hours (14400s) |
| Prefetch cache behavior | Complete rewrite with layout deduplication and incremental prefetching |
| revalidateTag() signature | Now requires cacheLife profile as second argument |

### Deprecations

- **middleware.ts filename** - Rename to `proxy.ts` to clarify network boundary
- **next/legacy/image component** - Use `next/image` instead
- **images.domains config** - Use `images.remotePatterns` config instead
- **revalidateTag() single argument** - Use `revalidateTag(tag, profile)` or `updateTag(tag)` in Actions

## Upgrade Instructions

```bash
# Use the automated upgrade CLI
npx @next/codemod@canary upgrade latest

# ...or upgrade manually
npm install next@latest react@latest react-dom@latest

# ...or start a new project
npx create-next-app@latest
```

