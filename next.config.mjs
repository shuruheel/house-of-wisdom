/** @type {import('next').NextConfig} */
const nextConfig = {
  // Turbopack is now default in Next.js 16, but explicit configuration available
  // Use --webpack flag to opt-out if needed

  // Optional: Enable Cache Components for fine-grained caching control
  // cacheComponents: true,

  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals.push('python-shell')
    }
    return config
  },
}

export default nextConfig
