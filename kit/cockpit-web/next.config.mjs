/** @type {import('next').NextConfig} */
const nextConfig = {
  // The Mac Pro's clients POST plain JSON from Python 2.7's urllib2, which
  // sends no Origin header. Nothing here should assume a browser.
  reactStrictMode: true,
};
export default nextConfig;
