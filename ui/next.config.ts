import type {NextConfig} from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone",
  async rewrites() {
    return [
      {
        source: "/videos/jobs/:promptId/:videoIndex",
        destination:
          "http://avatar-delivery:80/videos/jobs/:promptId/:videoIndex",
      },
      {
        source: "/v1/:path*",
        destination: "http://avatar-video-producer:9000/v1/:path*",
      },
    ];
  },
  experimental: {
    serverActions: {
      bodySizeLimit: "300mb",
    },
  },
};

export default nextConfig;
