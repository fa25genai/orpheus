import type {NextConfig} from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  async rewrites() {
    return [
      {
          source: '/videos/jobs/:promptId/:videoIndex',
          destination: 'http://avatar-delivery:80/videos/jobs/:promptId/:videoIndex',
      },
    ];
  }
};

export default nextConfig;
