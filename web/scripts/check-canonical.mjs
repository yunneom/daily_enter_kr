// GSC 재발 방지 게이트 (2026-07): dailyenterkr.com 에서 "표준 없는 중복 페이지" /
// "리디렉션 포함 페이지" 오류가 나온 근본 원인은 app/layout.tsx 의 전역
// metadata.alternates.canonical="/" 을 새 라우트(/play, /shop)가 override 하지
// 않아 홈의 canonical 을 조용히 상속한 것이었다. 이 스크립트는 그 버그 클래스가
// 다시 배포되는 것을 소스 레벨(빌드 전)에서 차단한다. 의존성 0 — 순수 node.
//
// 검사 항목:
//   a) app/sitemap.ts 에 등재된 모든 라우트를 정규식으로 추출
//   b) 각 라우트에 대응하는 app/<route>/page.tsx(홈은 app/page.tsx) 가 존재하고,
//      그 파일(또는 같은 디렉토리 layout.tsx) 이 자기 라우트 값으로 자기참조
//      canonical 을 선언하는지 확인
//   c) redirect(...) 를 호출하는 페이지(app/vote/page.tsx 등)가 사이트맵에
//      포함되지 않았는지 확인
//   d) app/layout.tsx 에 전역 canonical 선언이 재도입되지 않았는지 확인
//
// 위반 시 어떤 파일/라우트가 문제인지 stderr 로 출력하고 exit 1 — vercel.json 의
// buildCommand 에 물려 있어 위반 시 Vercel 배포 자체가 실패한다.
import fs from "node:fs";
import path from "node:path";

const webRoot = process.cwd();
const appDir = path.join(webRoot, "app");
const sitemapPath = path.join(appDir, "sitemap.ts");
const rootLayoutPath = path.join(appDir, "layout.tsx");

const errors = [];

function readFile(p) {
  return fs.readFileSync(p, "utf8");
}

// 주석 안의 "canonical" 언급(설명용 코멘트 등)이 오탐되지 않도록 코드에서
// 주석을 걷어내고 검사한다.
function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, "").replace(/\/\/.*$/gm, "");
}

function escapeRegExp(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

// app/sitemap.ts 의 `${SITE_URL}/route` 형태 템플릿 리터럴에서 경로만 추출.
function parseSitemapRoutes(src) {
  const routes = [];
  // 정적 라우트(`${SITE_URL}/play`) 와 동적 라우트(`${SITE_URL}/idols/${m.rank}`)
  // 를 모두 인식한다. 경로 안에 다시 `${...}` 가 들어가면 동적으로 분류.
  const re = /\$\{SITE_URL\}((?:[a-zA-Z0-9/_-]|\$\{[^}]*\})*)/g;
  let m;
  while ((m = re.exec(src)) !== null) {
    const raw = m[1];
    const dynIdx = raw.indexOf("${");
    if (dynIdx === -1) {
      routes.push({ kind: "static", route: raw === "" ? "/" : raw });
    } else {
      // "/idols/${m.rank}" → base "/idols"
      const base = raw.slice(0, dynIdx).replace(/\/+$/, "");
      if (base) routes.push({ kind: "dynamic", route: base });
    }
  }
  // 동일 라우트 중복 제거 (동적은 map 한 번에 하나만 잡히지만 방어적으로)
  const seen = new Set();
  return routes.filter((r) => {
    const k = `${r.kind}:${r.route}`;
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
}

// 동적 라우트 검증: app/<base>/[param]/page.tsx 가 존재하고, 각 항목이
// 자기 URL 을 canonical 로 만들어 쓰는지(템플릿 리터럴) 확인한다.
// 정적 라우트처럼 리터럴 일치로는 볼 수 없어 별도 규칙을 쓴다.
function checkDynamicRoute(base) {
  const baseDir = path.join(appDir, ...base.replace(/^\//, "").split("/").filter(Boolean));
  if (!fs.existsSync(baseDir)) {
    return `사이트맵 동적 라우트 "${base}/..." 의 디렉토리가 없습니다: ${path.relative(webRoot, baseDir)}`;
  }
  const paramDirs = fs
    .readdirSync(baseDir, { withFileTypes: true })
    .filter((e) => e.isDirectory() && /^\[.+\]$/.test(e.name));
  if (paramDirs.length === 0) {
    return `사이트맵 동적 라우트 "${base}/..." 에 대응하는 [param] 디렉토리가 없습니다: ${path.relative(webRoot, baseDir)}`;
  }
  for (const d of paramDirs) {
    const pageFile = path.join(baseDir, d.name, "page.tsx");
    if (!fs.existsSync(pageFile)) {
      return `동적 라우트 페이지가 없습니다: ${path.relative(webRoot, pageFile)}`;
    }
    const content = stripComments(readFile(pageFile));
    const rel = path.relative(webRoot, pageFile);
    const m = /alternates\s*:\s*\{\s*canonical\s*:\s*([^,}]+)/.exec(content);
    if (!m) {
      return `동적 라우트 "${base}/${d.name}" 가 alternates.canonical 을 선언하지 않았습니다: ${rel}`;
    }
    // canonical 에 실제로 대입된 "값" 을 본다. 파일 어딘가에 자기참조 URL 문자열이
    // 존재하는지만 보면, canonical 을 "/" 로 바꿔놔도 통과하는 가짜 검증이 된다.
    const value = m[1].trim();
    const selfTemplate = new RegExp("`" + escapeRegExp(base) + "/\\$\\{");

    if (/^["'`]/.test(value)) {
      // 리터럴 — 동적 라우트는 항목마다 URL 이 달라야 하므로 템플릿만 허용.
      if (!(value.startsWith("`") && selfTemplate.test(value))) {
        return (
          `동적 라우트 "${base}/${d.name}" 의 canonical 이 고정 문자열 ${value} 입니다 — ` +
          `항목마다 자기 URL(\`${base}/\${...}\`)을 canonical 로 선언하세요: ${rel}`
        );
      }
      continue;
    }
    // 식별자 → 그 변수가 자기 경로 템플릿으로 만들어졌는지 확인.
    const assigned = new RegExp(
      "(?:const|let|var)\\s+" + escapeRegExp(value) + "\\s*=\\s*`" + escapeRegExp(base) + "/\\$\\{",
    );
    if (!assigned.test(content)) {
      return (
        `동적 라우트 "${base}/${d.name}" 의 canonical 값 "${value}" 이 ` +
        `\`${base}/\${...}\` 로 생성되지 않습니다 — 자기참조 URL 을 대입하세요: ${rel}`
      );
    }
  }
  return null;
}

// 라우트 문자열 → 기대되는 page.tsx 절대경로. 홈("/")은 app/page.tsx.
function routeToPageFile(route) {
  if (route === "/") return path.join(appDir, "page.tsx");
  const segments = route.replace(/^\//, "").split("/").filter(Boolean);
  return path.join(appDir, ...segments, "page.tsx");
}

// page.tsx 절대경로 → 라우트 문자열 (routeToPageFile 의 역변환).
function pageFileToRoute(pageFile) {
  const rel = path.relative(appDir, path.dirname(pageFile)).split(path.sep).filter(Boolean);
  return rel.length === 0 ? "/" : `/${rel.join("/")}`;
}

function hasSelfCanonical(content, route) {
  const pattern = new RegExp(`canonical\\s*:\\s*["'\`]${escapeRegExp(route)}["'\`]`);
  return pattern.test(content);
}

function findAllPageFiles(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name === "node_modules" || entry.name === ".next") continue;
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...findAllPageFiles(full));
    } else if (entry.name === "page.tsx") {
      out.push(full);
    }
  }
  return out;
}

// --- 준비 ---
if (!fs.existsSync(sitemapPath)) {
  console.error(`[check-canonical] sitemap 없음: ${sitemapPath}`);
  process.exit(1);
}
if (!fs.existsSync(rootLayoutPath)) {
  console.error(`[check-canonical] root layout 없음: ${rootLayoutPath}`);
  process.exit(1);
}

const sitemapSrc = readFile(sitemapPath);
const sitemapRoutes = parseSitemapRoutes(sitemapSrc);
if (sitemapRoutes.length === 0) {
  errors.push(`sitemap.ts 에서 라우트를 하나도 파싱하지 못했습니다 (정규식 확인 필요): ${sitemapPath}`);
}

// --- (b) 사이트맵 라우트 ↔ 자기참조 canonical ---
for (const entry of sitemapRoutes) {
  const route = entry.route;
  if (entry.kind === "dynamic") {
    const err = checkDynamicRoute(route);
    if (err) errors.push(err);
    continue;
  }
  const pageFile = routeToPageFile(route);
  if (!fs.existsSync(pageFile)) {
    errors.push(`사이트맵 라우트 "${route}" 에 대응하는 페이지가 없습니다: ${path.relative(webRoot, pageFile)}`);
    continue;
  }
  const pageContent = stripComments(readFile(pageFile));
  const layoutFile = path.join(path.dirname(pageFile), "layout.tsx");
  const layoutContent =
    fs.existsSync(layoutFile) && layoutFile !== rootLayoutPath
      ? stripComments(readFile(layoutFile))
      : "";
  if (!hasSelfCanonical(pageContent, route) && !hasSelfCanonical(layoutContent, route)) {
    errors.push(
      `라우트 "${route}" 가 자기참조 canonical 을 선언하지 않았습니다 — ` +
        `${path.relative(webRoot, pageFile)} (또는 같은 디렉토리 layout.tsx) 에 ` +
        `alternates: { canonical: "${route}" } 를 추가하세요.`,
    );
  }
}

// --- (c) redirect() 페이지가 사이트맵에 없는지 ---
const sitemapRouteSet = new Set(
  sitemapRoutes.filter((r) => r.kind === "static").map((r) => r.route),
);
for (const pageFile of findAllPageFiles(appDir)) {
  const content = stripComments(readFile(pageFile));
  if (/\bredirect\s*\(/.test(content)) {
    const route = pageFileToRoute(pageFile);
    if (sitemapRouteSet.has(route)) {
      errors.push(
        `"${route}" (${path.relative(webRoot, pageFile)}) 는 redirect() 를 호출하는 페이지인데 ` +
          `sitemap.ts 에 포함되어 있습니다 — 리디렉션 URL 은 사이트맵에서 제외하세요.`,
      );
    }
  }
}

// --- (d) 전역 layout 에 canonical 재도입 여부 ---
const layoutContentStripped = stripComments(readFile(rootLayoutPath));
if (/canonical\s*:/.test(layoutContentStripped)) {
  errors.push(
    `app/layout.tsx 에 전역 canonical 선언이 있습니다 — 홈을 포함한 모든 라우트가 ` +
      `이를 override 하지 않으면 조용히 상속해 GSC 중복 페이지 오류로 이어집니다. ` +
      `canonical 은 각 라우트의 page.tsx 에서만 선언하세요.`,
  );
}

// --- 결과 ---
if (errors.length > 0) {
  console.error("[check-canonical] 위반 발견:\n");
  for (const e of errors) console.error(`  - ${e}`);
  console.error(`\n총 ${errors.length}건. 배포를 중단합니다.`);
  process.exit(1);
}

console.log(`[check-canonical] OK — 사이트맵 라우트 ${sitemapRoutes.length}개 모두 자기참조 canonical 확인, redirect 페이지 미포함, 전역 canonical 없음.`);
