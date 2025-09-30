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
      {
        source: '/v1/avatars/by-course/:courseId',
        destination: 'http://localhost:9000/v1/avatars/by-course/:courseId'
      },
      {
        source: '/v1/avatars/:courseId/:slot/image',
        destination: 'http://localhost:9000/v1/avatars/:courseId/:slot/image'
      }
    ];
  }
};

export default nextConfig;
