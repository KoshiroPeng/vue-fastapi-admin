const fs = require('fs')
const path = require('path')
const { spawnSync } = require('child_process')
const { findPlaceholders, readLocales, renderProjectText } = require('./locales')

const ROOT_DIR = path.resolve(__dirname, '..')
const TEXT_EXTENSIONS = new Set(['.css', '.html', '.js', '.json', '.jsp', '.txt'])

function assertProjectName(projectName) {
  if (!/^[a-z0-9][a-z0-9-]*$/i.test(projectName)) {
    throw new Error(`Invalid project name: ${projectName}`)
  }
}

function copyDirectory(sourceDir, outputDir) {
  fs.rmSync(outputDir, { recursive: true, force: true })
  fs.cpSync(sourceDir, outputDir, {
    recursive: true,
    filter: (source) => path.basename(source) !== '.DS_Store'
  })
}

function visitFiles(directory, callback) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const entryPath = path.join(directory, entry.name)
    if (entry.isDirectory()) visitFiles(entryPath, callback)
    else if (entry.isFile()) callback(entryPath)
  }
}

function renderDirectory(directory, locale, projectName, language, device) {
  visitFiles(directory, (filePath) => {
    if (!TEXT_EXTENSIONS.has(path.extname(filePath).toLowerCase())) return
    const source = renderProjectText(fs.readFileSync(filePath, 'utf8'), {
      activeLanguage: language,
      device,
      filePath,
      locale,
      projectName
    })
    fs.writeFileSync(filePath, source)
  })
}

function usesSharedDeviceSource(sourceDir) {
  return fs.readdirSync(sourceDir, { withFileTypes: true }).some((entry) =>
    entry.isFile() && /\.(html|jsp)$/i.test(entry.name)
  )
}

function buildLanguage(sourceDir, outputDir, locale, projectName, language, sharedDeviceSource) {
  if (!sharedDeviceSource) {
    copyDirectory(sourceDir, outputDir)
    renderDirectory(outputDir, locale, projectName, language)
    return
  }

  fs.rmSync(outputDir, { recursive: true, force: true })
  fs.mkdirSync(outputDir, { recursive: true })
  for (const device of ['phone', 'pc']) {
    const deviceOutputDir = path.join(outputDir, device)
    copyDirectory(sourceDir, deviceOutputDir)
    renderDirectory(deviceOutputDir, locale, projectName, language, device)
  }
}

function verifyRenderedDirectory(directory) {
  const unresolved = []
  visitFiles(directory, (filePath) => {
    if (!TEXT_EXTENSIONS.has(path.extname(filePath).toLowerCase())) return
    const source = fs.readFileSync(filePath, 'utf8')
    for (const key of findPlaceholders(source)) unresolved.push(`${path.relative(directory, filePath)}: ${key}`)
  })
  if (unresolved.length) throw new Error(`Unresolved locale placeholders remain:\n${unresolved.join('\n')}`)
}

function createArchive(sourceDir, archiveDir) {
  const archivePath = path.join(archiveDir, `${path.basename(sourceDir)}.zip`)
  fs.mkdirSync(archiveDir, { recursive: true })
  fs.rmSync(archivePath, { force: true })

  const result = spawnSync('zip', ['-q', '-r', archivePath, path.basename(sourceDir)], {
    cwd: path.dirname(sourceDir),
    encoding: 'utf8'
  })
  if (result.error) throw result.error
  if (result.status !== 0) throw new Error(result.stderr || `zip exited with status ${result.status}`)
  return archivePath
}

function removeLocalArchives(projectName, distDir) {
  for (const archiveName of [`${projectName}.zip`, `${projectName}_zh.zip`, `${projectName}_trl.zip`]) {
    fs.rmSync(path.join(distDir, archiveName), { force: true })
  }
}

function buildProject(projectName, options = {}) {
  assertProjectName(projectName)
  const projectDir = path.join(ROOT_DIR, projectName)
  const sourceDir = path.join(projectDir, 'source')
  const distDir = path.join(projectDir, 'dist')
  const zhDir = path.join(distDir, `${projectName}_zh`)
  const translatedDir = path.join(distDir, `${projectName}_trl`)

  if (!fs.existsSync(sourceDir)) throw new Error(`Source directory not found: ${sourceDir}`)
  const locales = readLocales(projectDir)
  const sharedDeviceSource = usesSharedDeviceSource(sourceDir)
  fs.mkdirSync(distDir, { recursive: true })
  buildLanguage(sourceDir, zhDir, locales.zh, projectName, 'zh', sharedDeviceSource)
  buildLanguage(sourceDir, translatedDir, locales.trl, projectName, 'trl', sharedDeviceSource)
  verifyRenderedDirectory(zhDir)
  verifyRenderedDirectory(translatedDir)

  removeLocalArchives(projectName, distDir)
  const archiveDir = options.archiveDir || path.join(ROOT_DIR, 'dist')
  const archivePaths = options.archive === false
    ? []
    : [createArchive(zhDir, archiveDir), createArchive(translatedDir, archiveDir)]
  return { archivePaths, sourceDir, translatedDir, zhDir }
}

if (require.main === module) {
  const projectName = process.argv[2]
  if (!projectName) {
    console.error('Usage: node scripts/build-project.js <project> [--no-archive]')
    process.exit(1)
  }

  try {
    const result = buildProject(projectName, { archive: !process.argv.includes('--no-archive') })
    console.log(`Generated: ${path.relative(ROOT_DIR, result.zhDir)}`)
    console.log(`Generated: ${path.relative(ROOT_DIR, result.translatedDir)}`)
    for (const archivePath of result.archivePaths) console.log(`Archive: ${path.relative(ROOT_DIR, archivePath)}`)
  } catch (error) {
    console.error(error.message)
    process.exit(1)
  }
}

module.exports = { buildProject }
