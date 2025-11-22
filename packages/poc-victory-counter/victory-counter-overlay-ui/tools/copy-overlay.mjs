import { cpSync, existsSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const projectRoot = dirname(__dirname);
const distDir = join(projectRoot, "dist");
const targetDir = join(projectRoot, "..", "victory-detector", "static", "overlay");

if (!existsSync(distDir)) {
  console.error("dist/ ディレクトリが見つかりません。まず `npm run build` を実行してください。");
  process.exit(1);
}

rmSync(targetDir, { recursive: true, force: true });
mkdirSync(targetDir, { recursive: true });
cpSync(distDir, targetDir, { recursive: true });

console.log(`Copied overlay build to ${targetDir}`);
