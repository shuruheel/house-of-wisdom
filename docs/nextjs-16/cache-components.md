# Cache Components

**URL:** https://nextjs.org/docs/app/getting-started/cache-components

Cache Components is a new approach to rendering and caching in Next.js that provides fine-grained control over what gets cached and when, while ensuring a great user experience through Partial Prerendering (PPR).

## Cache Components

When developing dynamic applications, you have to balance two primary approaches:

- Fully static pages load fast but can't show personalized or real-time data
- Fully dynamic pages can show fresh data but require rendering everything on each request, leading to slower initial loads

With Cache Components enabled, Next.js treats all routes as dynamic by default. Every request renders with the latest available data. However, most pages are made up of both static and dynamic parts, and not all dynamic data needs to be resolved from source on every request.

Cache Components allows you to mark data, and even parts of your UI as cacheable, which includes them in the pre-render pass alongside static parts of the page.

Before Cache Components, Next.js tried to statically optimize entire pages automatically, which could lead to unexpected behavior when adding dynamic code.

Cache Components implements Partial Prerendering (PPR), and use cache to give you the best of both worlds:

When a user visits a route:
- The server sends a static shell containing cached content, ensuring a fast initial load
- Dynamic sections wrapped in Suspense boundaries display fallback UI in the shell
- Only the dynamic parts render to replace their fallbacks, streaming in parallel as they become ready
- You can include otherwise-dynamic data in the initial shell by caching it with `use cache`

## How it works

**Good to know:** Cache Components is an opt-in feature. Enable it by setting the `cacheComponents` flag to true in your Next config file.

Cache Components gives you three key tools to control rendering:

### 1. Suspense for runtime data

Some data is only available at runtime when an actual user makes a request. APIs like `cookies`, `headers`, and `searchParams` access request-specific information. Wrap components using these APIs in Suspense boundaries so the rest of the page can be pre-rendered as a static shell.

Runtime APIs include:
- `cookies`
- `headers`
- `searchParams` prop
- `params` prop - This is runtime data unless you provide at least one example value through `generateStaticParams`. When provided, those specific param values are treated as static for prerendered paths, while other values remain runtime

### 2. Suspense for dynamic data

Dynamic data like fetch calls or database queries (`db.query(...)`) can change between requests but isn't user-specific. The `connection` API is meta-dynamic—it represents waiting for a user navigation even though there's no actual data to return. Wrap components that use these in Suspense boundaries to enable streaming.

Dynamic data patterns include:
- fetch requests
- Database queries
- `connection`

### 3. Cached data with use cache

Add `use cache` to any Server Component to make it cached and include it in the pre-rendered shell. You cannot use runtime APIs from inside a cached component. You can also mark utility functions as `use cache` and call them from Server Components.

```typescript
export async function getProducts() {
  'use cache'
  const data = await db.query('SELECT * FROM products')
  return data
}
```

## Using Suspense boundaries

React Suspense boundaries let you define what fallback UI to use when it wraps dynamic or runtime data.

Content outside the boundary, including the fallback UI, is pre-rendered as a static shell, while content inside the boundary streams in when ready.

Here's how to use Suspense with Cache Components:

```typescript
import { Suspense } from 'react'

export default function Page() {
  return (
    <>
      <h1>This will be pre-rendered</h1>
      <Suspense fallback={<Skeleton />}>
        <DynamicContent />
      </Suspense>
    </>
  )
}

async function DynamicContent() {
  const res = await fetch('http://api.cms.com/posts')
  const { posts } = await res.json()
  return <div>{/* ... */}</div>
}
```

At build time, Next.js pre-renders the static content and the fallback UI, while the dynamic content is postponed until a user requests the route.

**Good to know:** Wrapping a component in Suspense doesn't make it dynamic; your API usage does. Suspense acts as a boundary that encapsulates dynamic content and enables streaming.

### Missing Suspense boundaries

Cache Components enforces that dynamic code must be wrapped in a Suspense boundary. If you forget, you'll see the "Uncached data was accessed outside of <Suspense>" error.

To fix this, you can either:
- Wrap the component in a `<Suspense>` boundary
- Move the asynchronous await into a Cache Component (`"use cache"`)

Note that request-specific information, such as `params`, `cookies`, and `headers`, is not available during static prerendering, so it must be wrapped in `<Suspense>`.

## How streaming works

Streaming splits the route into chunks and progressively streams them to the client as they become ready. This allows the user to see parts of the page immediately, before the entire content has finished rendering.

With partial pre-rendering, the initial UI can be sent immediately to the browser while the dynamic parts render. This decreases time to UI and may decrease total request time depending on how much of your UI is pre-rendered.

To reduce network overhead, the full response, including static HTML and streamed dynamic parts, is sent in a single HTTP request.

## Using use cache

While Suspense boundaries manage dynamic content, the `use cache` directive is available for caching data or computations that don't change often.

### Basic usage

Add `use cache` to cache a page, component, or async function, and define a lifetime with `cacheLife`:

```typescript
import { cacheLife } from 'next/cache'

export default async function Page() {
  'use cache'
  cacheLife('hours')
  // fetch or compute
  return <div>...</div>
}
```

### Caveats

When using `use cache`, keep these constraints in mind:

**Arguments must be serializable**

Like Server Actions, arguments to cached functions must be serializable. This means you can pass primitives, plain objects, and arrays, but not class instances, functions, or other complex types.

**Accepting unserializable values without introspection**

You can accept unserializable values as arguments as long as you don't introspect them. However, you can return them. This allows patterns like cached components that accept Server or Client Components as children:

```typescript
import { ReactNode } from 'react'

export async function CachedWrapper({ children }: { children: ReactNode }) {
  'use cache'
  // Don't introspect children, just pass it through
  return (
    <div className="wrapper">
      <header>Cached Header</header>
      {children}
    </div>
  )
}
```

**Avoid passing dynamic inputs**

You must not pass dynamic or runtime data into use cache functions unless you avoid introspecting them.

## Tagging and revalidating

Tag cached data with `cacheTag` and revalidate it after mutations using `updateTag` in Server Actions for immediate updates, or `revalidateTag` if delays in updates are acceptable.

### With updateTag

Use `updateTag` when you need to expire and immediately refresh cached data within the same request:

```typescript
import { cacheTag, updateTag } from 'next/cache'

export async function getCart() {
  'use cache'
  cacheTag('cart')
  // fetch data
}

export async function updateCart(itemId: string) {
  'use server'
  // write data using the itemId
  // update the user cart
  updateTag('cart')
}
```

### With revalidateTag

Use `revalidateTag` when you want to invalidate only properly tagged cached entries with stale-while-revalidate behavior:

```typescript
import { cacheTag, revalidateTag } from 'next/cache'

export async function getPosts() {
  'use cache'
  cacheTag('posts')
  // fetch data
}

export async function createPost(post: FormData) {
  'use server'
  // write data using the FormData
  revalidateTag('posts', 'max')
}
```

## Enabling Cache Components

You can enable Cache Components (which includes PPR) by adding the `cacheComponents` option to your Next config file:

```typescript
import type { NextConfig } from 'next'

const nextConfig: NextConfig = {
  cacheComponents: true,
}

export default nextConfig
```

### Effect on route segment config

When Cache Components is enabled, several route segment config options are no longer needed or supported:

**`dynamic = "force-dynamic"`** - Not needed. All pages are dynamic by default.

**`dynamic = "force-static"`** - Replace with `use cache`.

**`revalidate`** - Replace with `cacheLife`.

**`fetchCache`** - Not needed. With `use cache`, all data fetching within a cached scope is automatically cached.

**`runtime = 'edge'`** - Not supported. Cache Components requires Node.js runtime.

## Before vs. after Cache Components

### Before Cache Components
- Static by default: Next.js tried to pre-render and cache as much as possible
- Route-level controls: Switches like `dynamic`, `revalidate`, `fetchCache` controlled caching for the whole page
- Limits of fetch: Using fetch alone was incomplete for database clients

### With Cache Components
- Dynamic by default: Everything is dynamic by default. You decide which parts to cache
- Fine-grained control: File/component/function-level `use cache` and `cacheLife` control caching exactly where you need it
- Streaming stays: Use `<Suspense>` to stream dynamic parts
- Beyond fetch: Using the `use cache` directive, caching can be applied to all server IO

## Examples

### Dynamic APIs

When accessing runtime APIs like `cookies()`, Next.js will only pre-render the fallback UI:

```typescript
import { cookies } from 'next/headers'

export async function User() {
  const session = (await cookies()).get('session')?.value
  return '...'
}
```

Wrap in Suspense:

```typescript
import { Suspense } from 'react'
import { User, AvatarSkeleton } from './user'

export default function Page() {
  return (
    <section>
      <h1>This will be pre-rendered</h1>
      <Suspense fallback={<AvatarSkeleton />}>
        <User />
      </Suspense>
    </section>
  )
}
```

### Passing dynamic props

Components only opt into dynamic rendering when the value is accessed:

```typescript
import { Table, TableSkeleton } from './table'
import { Suspense } from 'react'

export default function Page({
  searchParams,
}: {
  searchParams: Promise<{ sort: string }>
}) {
  return (
    <section>
      <h1>This will be pre-rendered</h1>
      <Suspense fallback={<TableSkeleton />}>
        <Table searchParams={searchParams.then((search) => search.sort)} />
      </Suspense>
    </section>
  )
}
```

## Frequently Asked Questions

**Does this replace Partial Prerendering (PPR)?**

No. Cache Components implements PPR as a feature. The old experimental PPR flag has been removed but PPR is here to stay.

**What should I cache first?**

What you cache should be a function of what you want your UI loading states to be. If data doesn't depend on runtime data and you're okay with a cached value being served for multiple requests over a period of time, use `use cache` with `cacheLife`.

**How do I update cached content quickly?**

Use `cacheTag` to tag your cached data, then trigger `updateTag` or `revalidateTag`.

