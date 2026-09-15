const fs = require('fs')
const path = require('path')
const { minify } = require('terser')

const ROOT_DIR = path.resolve(__dirname, '..')
const SOURCE_PATH = path.join(ROOT_DIR, 'pr', 'index.js')
const OUTPUT_DIR = path.join(ROOT_DIR, 'pr', 'dist')
const OUTPUT_PATH = path.join(OUTPUT_DIR, 'index.min.js')

async function build() {
  if (!fs.existsSync(SOURCE_PATH)) throw new Error(`Source file not found: ${SOURCE_PATH}`)

  const source = fs.readFileSync(SOURCE_PATH, 'utf8')
  const result = await minify(source, {
    compress: { passes: 3 },
    format: { ascii_only: true, beautify: false, comments: false },
    mangle: { reserved: ['PR'], toplevel: true },
    sourceMap: false
  })

  if (!result.code || !/\bPR\b/.test(result.code)) {
    throw new Error('Compressed output does not expose the required PR global.')
  }

  fs.rmSync(OUTPUT_DIR, { recursive: true, force: true })
  fs.mkdirSync(OUTPUT_DIR, { recursive: true })
  const output = `${result.code}\n`
  fs.writeFileSync(OUTPUT_PATH, output)

  const reduction = Math.round((1 - Buffer.byteLength(output) / Buffer.byteLength(source)) * 100)
  console.log(`Generated: ${path.relative(ROOT_DIR, OUTPUT_PATH)} (${reduction}% smaller)`)
}

build().catch((error) => {
  console.error(error.message)
  process.exit(1)
})
