/** @type {import('next').NextConfig} */
const nextConfig = {
    webpack: (config, { isServer }) => {
      if (isServer) {
        config.externals.push('python-shell')
      }
      return config
    },
  }
  
  export default nextConfig