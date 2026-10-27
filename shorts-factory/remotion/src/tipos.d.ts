// Webpack (Remotion) convierte los .woff2 importados en URLs servidas por el bundle.
declare module "*.woff2" {
  const url: string;
  export default url;
}
