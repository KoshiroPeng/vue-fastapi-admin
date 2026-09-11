const fs = require('fs')
const path = require('path')
const { buildProject } = require('./build-project')

const ROOT_DIR = path.resolve(__dirname, '..')
const ARCHIVE_DIR = path.join(ROOT_DIR, 'dist')

const projects = fs.readdirSync(ROOT_DIR, { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .filter((projectName) =>
    fs.existsSync(path.join(ROOT_DIR, projectName, 'source')) &&
    fs.existsSync(path.join(ROOT_DIR, projectName, 'locales', 'zh.json')) &&
    fs.existsSync(path.join(ROOT_DIR, projectName, 'locales', 'trl.json'))
  )
  .sort((left, right) => left.localeCompare(right, 'zh-CN'))

if (!projects.length) {
  console.error('No localizable portal projects found.')
  process.exit(1)
}

try {
  fs.rmSync(ARCHIVE_DIR, { recursive: true, force: true })
  fs.mkdirSync(ARCHIVE_DIR, { recursive: true })
  for (const projectName of projects) {
    const result = buildProject(projectName, { archiveDir: ARCHIVE_DIR })
    for (const archivePath of result.archivePaths) console.log(`${projectName}: ${path.relative(ROOT_DIR, archivePath)}`)
  }
} catch (error) {
  console.error(error.message)
  process.exit(1)
}
