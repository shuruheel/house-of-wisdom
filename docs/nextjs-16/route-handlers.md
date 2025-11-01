# Route Handlers

**URL:** https://nextjs.org/docs/app/getting-started/route-handlers

Route Handlers allow you to create custom request handlers for a given route using the Web Request and Response APIs.

**Good to know:** Route Handlers are only available inside the app directory. They are the equivalent of API Routes inside the pages directory meaning you do not need to use API Routes and Route Handlers together.

## Convention

Route Handlers are defined in a `route.js|ts` file inside the app directory:

```typescript
// app/api/route.ts
export async function GET(request: Request) {}
```

Route Handlers can be nested anywhere inside the app directory, similar to `page.js` and `layout.js`. But there cannot be a `route.js` file at the same route segment level as `page.js`.

## Supported HTTP Methods

The following HTTP methods are supported: **GET, POST, PUT, PATCH, DELETE, HEAD, and OPTIONS**. If an unsupported method is called, Next.js will return a 405 Method Not Allowed response.

## Extended NextRequest and NextResponse APIs

In addition to supporting the native Request and Response APIs, Next.js extends them with `NextRequest` and `NextResponse` to provide convenient helpers for advanced use cases.

## Caching

Route Handlers are **not cached by default**. You can, however, opt into caching for GET methods. Other supported HTTP methods are not cached. To cache a GET method, use a route config option such as `export const dynamic = 'force-static'` in your Route Handler file.

```typescript
// app/items/route.ts
export const dynamic = 'force-static'

export async function GET() {
  const res = await fetch('https://data.mongodb-api.com/...', {
    headers: {
      'Content-Type': 'application/json',
      'API-Key': process.env.DATA_API_KEY,
    },
  })
  const data = await res.json()

  return Response.json({ data })
}
```

**Good to know:** Other supported HTTP methods are not cached, even if they are placed alongside a GET method that is cached, in the same file.

## Special Route Handlers

Special Route Handlers like `sitemap.ts`, `opengraph-image.tsx`, and `icon.tsx`, and other metadata files remain static by default unless they use Dynamic APIs or dynamic config options.

## Route Resolution

You can consider a route the lowest level routing primitive.

- They do not participate in layouts or client-side navigations like page.
- There cannot be a `route.js` file at the same route as `page.js`.

| Page                      | Route                  | Result    |
|---------------------------|------------------------|-----------|
| `app/page.js`             | `app/route.js`         | ❌ Conflict |
| `app/page.js`             | `app/api/route.js`     | ✅ Valid   |
| `app/[user]/page.js`      | `app/api/route.js`     | ✅ Valid   |

Each `route.js` or `page.js` file takes over all HTTP verbs for that route.

```typescript
// app/page.ts
export default function Page() {
  return <h1>Hello, Next.js!</h1>
}

// Conflict
// `app/route.ts`
export async function POST(request: Request) {}
```

## Route Context Helper

In TypeScript, you can type the context parameter for Route Handlers with the globally available `RouteContext` helper:

```typescript
// app/users/[id]/route.ts
import type { NextRequest } from 'next/server'

export async function GET(_req: NextRequest, ctx: RouteContext<'/users/[id]'>) {
  const { id } = await ctx.params
  return Response.json({ id })
}
```

**Good to know:** Types are generated during `next dev`, `next build` or `next typegen`.

