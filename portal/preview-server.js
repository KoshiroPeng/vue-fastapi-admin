const fs = require('fs')
const http = require('http')
const os = require('os')
const path = require('path')
const { readLocale, renderProjectText } = require('./scripts/locales')

const ROOT_DIR = __dirname
const MODE = process.argv.includes('--dev') ? 'dev' : 'preview'
const START_PORT = Number.parseInt(process.env.PORT || process.env.PREVIEW_PORT || '3300', 10)

function readArgument(name) {
  const index = process.argv.indexOf(name)
  if (index === -1) return null
  const value = process.argv[index + 1]
  return value && !value.startsWith('--') ? value : null
}

const HOST = readArgument('--host') || process.env.PREVIEW_HOST || '0.0.0.0'

const excludedDirectories = new Set(['.git', 'node_modules', 'phone-ui'])
const projectLabels = {
  entrance: '认证入口',
  passport: '护照认证',
  sms: '短信认证',
  boarding: '登机牌认证',
  'boarding-pass': '登机牌认证',
  wechat: '微信小程序认证',
  kiosk: '取号机认证',
  'kiosk-account': '取号机认证'
}
const projectOrder = ['entrance', 'sms', 'passport', 'wechat', 'boarding-pass', 'boarding', 'kiosk-account', 'kiosk']
const languageLabels = { zh: '简体中文', trl: '繁體中文' }
const languageOrder = ['zh', 'trl', 'unknown']
const deviceLabels = { phone: 'Phone', pc: 'PC' }
const deviceOrder = ['phone', 'pc']
const pageLabels = { auth: '认证页', authSuccess: '认证成功', readme: '用户须知' }
const pageOrder = ['auth', 'authSuccess', 'readme']

function detectLanguage(templateName) {
  const normalized = templateName.toLowerCase()
  if (/(^|[_-])trl([_-]|$)/.test(normalized)) return 'trl'
  if (/(^|[_-])zh([_-]|$)/.test(normalized)) return 'zh'
  return 'unknown'
}

function formatProjectLabel(projectName) {
  return projectLabels[projectName.toLowerCase()] || projectName.replace(/[-_]+/g, ' ')
}

function sortIndex(values, value) {
  const index = values.indexOf(value)
  return index === -1 ? values.length : index
}

function toPreviewPath(segments) {
  return `/${segments.map(encodeURIComponent).join('/')}`
}

function scanPreviewGroups() {
  const groups = new Map()

  function addPage(project, language, device, pageId, pagePath, template) {
    const page = {
      device,
      label: `${languageLabels[language]} / ${deviceLabels[device]} / ${pageLabels[pageId]}`,
      language,
      pageId,
      path: pagePath,
      template
    }
    if (!groups.has(project)) groups.set(project, { id: project, label: formatProjectLabel(project), pages: [] })
    groups.get(project).pages.push(page)
  }

  function visitPreview(directory, segments) {
    let entries
    try {
      entries = fs.readdirSync(directory, { withFileTypes: true })
    } catch {
      return
    }

    for (const entry of entries) {
      if (entry.name.startsWith('.') || excludedDirectories.has(entry.name)) continue
      const nextSegments = [...segments, entry.name]
      const entryPath = path.join(directory, entry.name)

      if (entry.isDirectory()) {
        visitPreview(entryPath, nextSegments)
        continue
      }

      const match = /^(auth|authSuccess|readme)\.(html|jsp)$/i.exec(entry.name)
      if (!entry.isFile() || !match || nextSegments.length < 4) continue

      const device = nextSegments[nextSegments.length - 2].toLowerCase()
      if (!deviceLabels[device]) continue

      const project = nextSegments[0]
      const template = nextSegments[nextSegments.length - 3]
      const matchedPage = match[1].toLowerCase()
      const pageId = matchedPage === 'authsuccess' ? 'authSuccess' : matchedPage
      const language = detectLanguage(template)
      if (language === 'unknown') continue
      addPage(project, language, device, pageId, toPreviewPath(nextSegments), template)
    }
  }

  function visitDev(project, directory, segments = []) {
    let entries
    try {
      entries = fs.readdirSync(directory, { withFileTypes: true })
    } catch {
      return
    }

    for (const entry of entries) {
      if (entry.name.startsWith('.')) continue
      const entryPath = path.join(directory, entry.name)
      const nextSegments = [...segments, entry.name]
      if (entry.isDirectory()) {
        visitDev(project, entryPath, nextSegments)
        continue
      }
      const match = /^(auth|authSuccess|readme)\.(html|jsp)$/i.exec(entry.name)
      if (!entry.isFile() || !match) continue
      const matchedPage = match[1].toLowerCase()
      const pageId = matchedPage === 'authsuccess' ? 'authSuccess' : matchedPage

      if (nextSegments.length === 1) {
        for (const language of ['zh', 'trl']) {
          for (const device of deviceOrder) {
            addPage(project, language, device, pageId, toPreviewPath(['__dev', project, language, device, entry.name]), 'source')
          }
        }
        continue
      }

      const device = nextSegments[nextSegments.length - 2].toLowerCase()
      if (!deviceLabels[device]) continue
      for (const language of ['zh', 'trl']) {
        addPage(project, language, device, pageId, toPreviewPath(['__dev', project, language, ...nextSegments]), 'source')
      }
    }
  }

  if (MODE === 'dev') {
    for (const project of getLocalizableProjects()) visitDev(project, path.join(ROOT_DIR, project, 'source'))
  } else {
    for (const entry of fs.readdirSync(ROOT_DIR, { withFileTypes: true })) {
      if (!entry.isDirectory() || entry.name.startsWith('.') || excludedDirectories.has(entry.name)) continue
      const distDir = path.join(ROOT_DIR, entry.name, 'dist')
      if (fs.existsSync(distDir)) visitPreview(distDir, [entry.name, 'dist'])
    }
  }

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      pages: group.pages.sort((left, right) =>
        sortIndex(languageOrder, left.language) - sortIndex(languageOrder, right.language) ||
        sortIndex(deviceOrder, left.device) - sortIndex(deviceOrder, right.device) ||
        sortIndex(pageOrder, left.pageId) - sortIndex(pageOrder, right.pageId) ||
        left.path.localeCompare(right.path, 'zh-CN')
      )
    }))
    .sort((left, right) =>
      sortIndex(projectOrder, left.id.toLowerCase()) - sortIndex(projectOrder, right.id.toLowerCase()) ||
      left.label.localeCompare(right.label, 'zh-CN')
    )
}

function getLocalizableProjects() {
  return fs.readdirSync(ROOT_DIR, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && !excludedDirectories.has(entry.name))
    .map((entry) => entry.name)
    .filter((projectName) =>
      fs.existsSync(path.join(ROOT_DIR, projectName, 'source')) &&
      fs.existsSync(path.join(ROOT_DIR, projectName, 'locales', 'zh.json')) &&
      fs.existsSync(path.join(ROOT_DIR, projectName, 'locales', 'trl.json'))
    )
}

const mimeTypes = {
  '.css': 'text/css; charset=utf-8',
  '.gif': 'image/gif',
  '.html': 'text/html; charset=utf-8',
  '.ico': 'image/x-icon',
  '.jpeg': 'image/jpeg',
  '.jpg': 'image/jpeg',
  '.js': 'text/javascript; charset=utf-8',
  '.jsp': 'text/html; charset=utf-8',
  '.json': 'application/json',
  '.png': 'image/png',
  '.svg': 'image/svg+xml; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
  '.webp': 'image/webp'
}
const localizableTextExtensions = new Set(['.css', '.html', '.js', '.json', '.jsp', '.txt'])

const reloadClients = new Set()
const previewClient = `(() => {
  const events = new EventSource('/__preview/events')
  events.addEventListener('reload', () => window.location.reload())
})()`

const verificationCodePlaceholder = `<svg xmlns="http://www.w3.org/2000/svg" width="118" height="58" viewBox="0 0 118 58">
  <rect width="118" height="58" fill="#f4f7fb"/>
  <path d="M8 42L110 15M14 13L104 45" stroke="#cbd7e7" stroke-width="1"/>
  <text x="59" y="36" fill="#315f9d" font-family="Arial,sans-serif" font-size="22" text-anchor="middle">8K3P</text>
</svg>`

const jqueryShim = `(() => {
  class Collection {
    constructor(value) { this.elements = value == null ? [] : value instanceof NodeList || Array.isArray(value) ? Array.from(value) : [value] }
    attr(name, value) { if (value === undefined) return this.elements[0]?.getAttribute?.(name); this.elements.forEach((e) => value == null || value === false ? e.removeAttribute?.(name) : e.setAttribute?.(name, value)); return this }
    val(value) { if (value === undefined) return this.elements[0]?.value; this.elements.forEach((e) => { e.value = value }); return this }
    addClass(name) { this.elements.forEach((e) => e.classList?.add(name)); return this }
    removeClass(name) { this.elements.forEach((e) => e.classList?.remove(name)); return this }
  }
  function jquery(value) { if (typeof value === 'function') return value(); if (typeof value === 'string') return new Collection(document.querySelectorAll(value)); return new Collection(value) }
  window.$ = window.jQuery = jquery
})()`

function send(res, statusCode, contentType, body) {
  res.writeHead(statusCode, { 'Cache-Control': 'no-store', 'Content-Type': contentType })
  res.end(body)
}

function renderDashboard() {
  const previewGroups = scanPreviewGroups()
  const preferredDefault = MODE === 'dev'
    ? '/__dev/entrance/zh/phone/auth.html'
    : '/entrance/dist/entrance_zh/phone/auth.html'
  const allPages = previewGroups.flatMap((group) => group.pages)
  const defaultPage = allPages.some((page) => page.path === preferredDefault)
    ? preferredDefault
    : allPages[0]?.path || 'about:blank'
  const dashboardTitle = MODE === 'dev' ? 'Wi-Fi 门户开发' : 'Wi-Fi 门户预览'
  const dashboardSummary = MODE === 'dev' ? 'DEV · Source + locales' : 'DIST · 构建产物'
  const catalog = previewGroups.flatMap((group) => group.pages.map((page) => ({
    ...page,
    project: group.id,
    projectLabel: group.label,
    title: `${group.label} / ${page.label}`
  })))
  const defaultEntry = catalog.find((page) => page.path === defaultPage)
  const defaultTitle = defaultEntry?.title || '未发现可预览页面'
  const catalogJson = JSON.stringify(catalog).replace(/</g, '\\u003c')
  const projects = previewGroups.map((group) =>
    `<button class="project-button" type="button" data-project="${group.id}"><span>${group.label}</span><span class="project-marker" aria-hidden="true"></span></button>`
  ).join('')

  return `<!doctype html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${dashboardTitle}</title><style>
  :root { --canvas: #e9edf2; --panel: #ffffff; --panel-subtle: #f7f8fa; --line: #d9dee6; --ink: #202733; --muted: #727c89; --accent: #2463eb; --accent-ink: #174ea6; --accent-soft: #edf3ff; color: var(--ink); background: var(--canvas); font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", Arial, sans-serif; }
  * { box-sizing: border-box; letter-spacing: 0; } html, body { width: 100%; height: 100%; margin: 0; } body { overflow: hidden; } a { color: inherit; text-decoration: none; } button { color: inherit; font: inherit; }
  .workspace { display: grid; grid-template-columns: 248px minmax(0, 1fr); width: 100%; height: 100%; }
  .sidebar { display: grid; grid-template-rows: auto auto minmax(0, 1fr); overflow: hidden; background: var(--panel); border-right: 1px solid var(--line); }
  .sidebar-header { padding: 18px 18px 16px; border-bottom: 1px solid var(--line); }
  h1 { margin: 0; color: #171d27; font-size: 18px; font-weight: 680; } .summary { margin: 6px 0 0; color: var(--muted); font: 11px/1.35 Menlo, Consolas, monospace; }
  .filters { display: grid; gap: 12px; padding: 14px 16px 16px; border-bottom: 1px solid var(--line); background: var(--panel-subtle); }
  .filter-row { display: grid; grid-template-columns: 38px minmax(0, 1fr); align-items: center; gap: 8px; }
  .filter-label, .project-label { color: var(--muted); font-size: 11px; font-weight: 650; }
  .segmented { display: grid; gap: 2px; padding: 2px; border: 1px solid #d5dbe4; border-radius: 5px; background: #eceff3; }
  .segmented[data-filter="language"], .segmented[data-filter="device"] { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .segmented[data-filter="pageId"] { grid-template-columns: repeat(3, minmax(0, 1fr)); }
  .filter-button { min-width: 0; height: 28px; padding: 0 5px; border: 0; border-radius: 3px; background: transparent; color: #536070; cursor: pointer; font-size: 12px; white-space: nowrap; }
  .filter-button:hover:not(:disabled) { background: #e1e6ec; color: var(--ink); } .filter-button.is-active { background: var(--panel); color: var(--accent-ink); box-shadow: 0 1px 3px rgba(39, 51, 69, .14); font-weight: 650; }
  .filter-button:disabled { cursor: not-allowed; opacity: .32; }
  .project-nav { min-height: 0; overflow-y: auto; padding: 14px 10px; }
  .project-label { display: block; padding: 0 8px 7px; }
  .project-list { display: grid; gap: 2px; }
  .project-button { display: flex; align-items: center; justify-content: space-between; width: 100%; height: 38px; padding: 0 10px; border: 0; border-radius: 4px; background: transparent; cursor: pointer; font-size: 13px; text-align: left; }
  .project-button:hover { background: #f1f3f6; } .project-button.is-active { background: var(--accent-soft); color: var(--accent-ink); box-shadow: inset 3px 0 var(--accent); font-weight: 650; }
  .project-marker { width: 6px; height: 6px; border-radius: 50%; background: transparent; } .project-button.is-active .project-marker { background: var(--accent); }
  .filter-button:focus-visible, .project-button:focus-visible, .open-link:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .filter-button:active:not(:disabled), .project-button:active, .open-link:active { transform: translateY(1px); }
  .preview-panel { display: grid; grid-template-rows: 58px minmax(0, 1fr); min-width: 0; min-height: 0; } .toolbar { display: flex; align-items: center; gap: 14px; padding: 0 20px; background: var(--panel); border-bottom: 1px solid var(--line); }
  .selection { min-width: 0; flex: 1; } .selection-title, .selection-path { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } .selection-title { font-size: 14px; font-weight: 650; } .selection-path { margin-top: 3px; color: var(--muted); font: 11px/1.2 Menlo, Consolas, monospace; }
  .open-link { flex: none; padding: 7px 10px; border: 1px solid #cfd6e0; border-radius: 4px; background: var(--panel); font-size: 12px; } .open-link:hover { border-color: #8eaeef; color: var(--accent-ink); }
  .stage { display: flex; align-items: center; justify-content: center; min-width: 0; min-height: 0; padding: 20px; overflow: auto; background: var(--canvas); }
  .frame-shell { width: min(390px, 100%); height: min(844px, 100%); min-height: 600px; overflow: hidden; background: var(--panel); border: 1px solid #cbd2dc; box-shadow: 0 10px 28px rgba(51, 62, 78, .13); } .frame-shell.is-pc { width: min(1280px, 100%); height: auto; min-height: 0; aspect-ratio: 16 / 9; } iframe { display: block; width: 100%; height: 100%; border: 0; }
  @media (max-width: 760px) { body { overflow: auto; } .workspace { grid-template-columns: 1fr; grid-template-rows: auto 78dvh; height: auto; min-height: 100%; } .sidebar { overflow: visible; } .project-nav { overflow: visible; } .project-list { grid-template-columns: repeat(2, minmax(0, 1fr)); } .toolbar { padding: 0 14px; } .stage { padding: 12px; } .frame-shell { height: 720px; } .frame-shell.is-pc { height: auto; } }
  </style></head><body><div class="workspace"><aside class="sidebar"><header class="sidebar-header"><h1>${dashboardTitle}</h1><p class="summary">${dashboardSummary}</p></header><section class="filters" aria-label="页面筛选"><div class="filter-row"><span class="filter-label">语言</span><div class="segmented" data-filter="language"><button class="filter-button" type="button" data-value="zh">简体</button><button class="filter-button" type="button" data-value="trl">繁体</button></div></div><div class="filter-row"><span class="filter-label">设备</span><div class="segmented" data-filter="device"><button class="filter-button" type="button" data-value="phone">Phone</button><button class="filter-button" type="button" data-value="pc">PC</button></div></div><div class="filter-row"><span class="filter-label">页面</span><div class="segmented" data-filter="pageId"><button class="filter-button" type="button" data-value="auth">认证</button><button class="filter-button" type="button" data-value="authSuccess">成功</button><button class="filter-button" type="button" data-value="readme">须知</button></div></div></section><nav class="project-nav" aria-label="认证项目"><span class="project-label">认证项目</span><div class="project-list">${projects}</div></nav></aside><main class="preview-panel"><header class="toolbar"><div class="selection"><div class="selection-title" id="selection-title">${defaultTitle}</div><div class="selection-path" id="selection-path">${defaultPage}</div></div><a class="open-link" id="open-link" href="${defaultPage}" target="_blank" rel="noopener">新窗口打开</a></header><div class="stage"><div class="frame-shell" id="frame-shell"><iframe id="preview-frame" name="preview-frame" title="Wi-Fi 门户页面预览" src="${defaultPage}"></iframe></div></div></main></div><script>
  const catalog = ${catalogJson}; const frame = document.getElementById('preview-frame'); const frameShell = document.getElementById('frame-shell'); const title = document.getElementById('selection-title'); const pathLabel = document.getElementById('selection-path'); const openLink = document.getElementById('open-link'); const projectButtons = Array.from(document.querySelectorAll('[data-project]')); const filterGroups = Array.from(document.querySelectorAll('[data-filter]')); let activePage = catalog.find((page) => page.path === ${JSON.stringify(defaultPage)}) || catalog[0];
  function findBest(preference) { const projectPages = catalog.filter((page) => page.project === preference.project); const candidates = projectPages.length ? projectPages : catalog; return candidates.find((page) => page.language === preference.language && page.device === preference.device && page.pageId === preference.pageId) || candidates.find((page) => page.language === preference.language && page.device === preference.device) || candidates.find((page) => page.language === preference.language && page.pageId === preference.pageId) || candidates.find((page) => page.device === preference.device && page.pageId === preference.pageId) || candidates[0]; }
  function updateControls() { frameShell.classList.toggle('is-pc', activePage.device === 'pc'); projectButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.project === activePage.project)); filterGroups.forEach((group) => { const field = group.dataset.filter; group.querySelectorAll('[data-value]').forEach((button) => { button.classList.toggle('is-active', button.dataset.value === activePage[field]); button.disabled = !catalog.some((page) => page.project === activePage.project && page[field] === button.dataset.value); }); }); }
  function selectPage(page, navigate = true) { if (!page) return; activePage = page; title.textContent = page.title; pathLabel.textContent = page.path; openLink.href = page.path; updateControls(); if (navigate && frame.getAttribute('src') !== page.path) frame.src = page.path; const url = new URL(window.location.href); url.searchParams.set('page', page.path); window.history.replaceState(null, '', url); }
  projectButtons.forEach((button) => button.addEventListener('click', () => selectPage(findBest({ ...activePage, project: button.dataset.project })))); filterGroups.forEach((group) => group.querySelectorAll('[data-value]').forEach((button) => button.addEventListener('click', () => selectPage(findBest({ ...activePage, [group.dataset.filter]: button.dataset.value })))))
  frame.addEventListener('load', () => { try { const page = catalog.find((item) => item.path === frame.contentWindow.location.pathname); if (page && page.path !== activePage.path) selectPage(page, false); } catch {} });
  const requested = new URL(window.location.href).searchParams.get('page'); selectPage(catalog.find((page) => page.path === requested) || activePage);
  </script><script src="/__preview/client.js"></script></body></html>`
}

function resolveWithin(rootDir, relativePath) {
  const filePath = path.resolve(rootDir, relativePath)
  if (filePath !== rootDir && !filePath.startsWith(`${rootDir}${path.sep}`)) return null
  try { return fs.statSync(filePath).isFile() ? filePath : null } catch { return null }
}

function resolvePreviewFile(pathname) {
  const relativePath = pathname.replace(/^\/+/, '')
  const segments = relativePath.split('/')
  if (segments.length < 3 || segments[1] !== 'dist') return null
  return resolveWithin(ROOT_DIR, relativePath)
}

function resolveDevFile(pathname) {
  const match = /^\/__dev\/([a-z0-9-]+)\/(zh|trl)\/(phone|pc)\/(.+)$/i.exec(pathname)
  if (!match) return null
  const [, projectName, language, device, relativePath] = match
  if (!getLocalizableProjects().includes(projectName)) return null
  const sourceDir = path.join(ROOT_DIR, projectName, 'source')
  const filePath = resolveWithin(sourceDir, relativePath) || resolveWithin(path.join(sourceDir, device), relativePath)
  return filePath ? { device, filePath, language, projectName, relativePath } : null
}

function renderDevText(file, source) {
  const projectDir = path.join(ROOT_DIR, file.projectName)
  const locale = readLocale(projectDir, file.language)
  const rendered = renderProjectText(source, {
    activeLanguage: file.language,
    device: file.device,
    filePath: file.filePath,
    hrefForLanguage: (language, device, pageName) => `/__dev/${file.projectName}/${language}/${device}/${pageName}`,
    locale,
    projectName: file.projectName
  })
  return rendered.replace(/\/([a-z0-9-]+)\/dist\/\1_(?:zh|trl)\//gi, (_match, targetProject) =>
    `/__dev/${targetProject}/${file.language}/`
  )
}

function renderHtml(source) {
  const withShims = source.replace(/<script[^>]+src="[^\"]*material\/custom\/jquery[^\"]*"[^>]*><\/script>/gi, '<script src="/__preview/jquery-shim.js"></script>')
  return withShims.includes('</body>') ? withShims.replace('</body>', '<script src="/__preview/client.js"></script></body>') : `${withShims}<script src="/__preview/client.js"></script>`
}

function requestHandler(req, res) {
  let pathname
  try { pathname = decodeURIComponent(new URL(req.url, `http://${req.headers.host || 'localhost'}`).pathname) } catch { send(res, 400, mimeTypes['.txt'], 'Invalid URL'); return }
  if (pathname === '/') { send(res, 200, mimeTypes['.html'], renderDashboard()); return }
  if (pathname === '/__preview/client.js') { send(res, 200, mimeTypes['.js'], previewClient); return }
  if (pathname === '/__preview/jquery-shim.js') { send(res, 200, mimeTypes['.js'], jqueryShim); return }
  if (pathname === '/portalauth/verificationcode') { send(res, 200, mimeTypes['.svg'], verificationCodePlaceholder); return }
  if (pathname === '/__preview/events') { res.writeHead(200, { 'Cache-Control': 'no-cache', Connection: 'keep-alive', 'Content-Type': 'text/event-stream' }); res.write(': connected\n\n'); reloadClients.add(res); req.on('close', () => reloadClients.delete(res)); return }
  if (/^\/material\/custom\/.*\.js$/.test(pathname)) { send(res, 200, mimeTypes['.js'], ''); return }
  if (/^\/material\/custom\/.*\.css$/.test(pathname)) { send(res, 200, mimeTypes['.css'], ''); return }
  const devFile = MODE === 'dev' ? resolveDevFile(pathname) : null
  const filePath = devFile?.filePath || (MODE === 'preview' ? resolvePreviewFile(pathname) : null)
  if (!filePath) { send(res, 404, mimeTypes['.txt'], `${MODE === 'dev' ? 'Development' : 'Preview'} file not found: ${pathname}`); return }
  const extension = path.extname(filePath).toLowerCase()
  try {
    if (devFile && localizableTextExtensions.has(extension)) {
      let body = renderDevText(devFile, fs.readFileSync(filePath, 'utf8'))
      if (extension === '.html' || extension === '.jsp') body = renderHtml(body)
      send(res, 200, mimeTypes[extension] || mimeTypes['.txt'], body)
      return
    }
    if (extension === '.html' || extension === '.jsp') {
      send(res, 200, mimeTypes[extension], renderHtml(fs.readFileSync(filePath, 'utf8')))
      return
    }
    res.writeHead(200, { 'Cache-Control': 'no-store', 'Content-Type': mimeTypes[extension] || 'application/octet-stream' })
    fs.createReadStream(filePath).pipe(res)
  } catch (error) {
    send(res, 500, mimeTypes['.txt'], `Unable to read ${MODE} file: ${error.message}`)
  }
}

function broadcastReload() { for (const client of reloadClients) client.write('event: reload\ndata: changed\n\n') }
let reloadTimer
try {
  fs.watch(ROOT_DIR, { recursive: true }, (_event, filename) => {
    if (!filename || filename.includes(`${path.sep}.git${path.sep}`)) return
    const segments = filename.split(path.sep)
    const watchedDirectory = MODE === 'dev'
      ? segments[1] === 'source' || segments[1] === 'locales'
      : segments[1] === 'dist'
    if (!watchedDirectory) return
    clearTimeout(reloadTimer)
    reloadTimer = setTimeout(broadcastReload, 100)
  })
} catch (error) {
  console.warn(`Automatic reload is unavailable: ${error.message}`)
}

function getAccessUrls(port) {
  const hosts = new Set()
  if (HOST === '0.0.0.0' || HOST === '::') {
    hosts.add('localhost')
    for (const addresses of Object.values(os.networkInterfaces())) {
      for (const address of addresses || []) {
        if (address.family === 'IPv4' && !address.internal) hosts.add(address.address)
      }
    }
  } else {
    hosts.add(HOST)
  }
  return Array.from(hosts, (host) => `http://${host}:${port}`)
}

function listen(port) {
  const server = http.createServer(requestHandler)
  server.on('error', (error) => {
    if (error.code === 'EADDRINUSE' && port < START_PORT + 20) {
      listen(port + 1)
      return
    }
    throw error
  })
  server.listen(port, HOST, () => {
    console.log(`Wi-Fi portal ${MODE}:`)
    for (const url of getAccessUrls(port)) console.log(`  ${url}`)
    console.log('Press Ctrl+C to stop.')
  })
}
listen(START_PORT)
