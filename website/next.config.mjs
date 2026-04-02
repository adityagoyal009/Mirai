/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/",
        destination: "/landing.html",
      },
      {
        source: "/report/:id",
        destination: "http://127.0.0.1:5000/report/:id",
      },
    ];
  },
};

export default nextConfig;
