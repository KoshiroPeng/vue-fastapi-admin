const fs = require('fs')
const path = require('path')

const PLACEHOLDER_PATTERN = /\{\{\s*([a-zA-Z0-9_.-]+)\s*\}\}/g

function readLocale(projectDir, language) {
  const filePath = path.join(projectDir, 'locales', `${language}.json`)
  return JSON.parse(fs.readFileSync(filePath, 'utf8'))
}

function readLocales(projectDir) {
  const zh = readLocale(projectDir, 'zh')
  const trl = readLocale(projectDir, 'trl')
  const missingKeys = Object.keys(zh).filter((key) => !(key in trl))
  const extraKeys = Object.keys(trl).filter((key) => !(key in zh))

  if (missingKeys.length || extraKeys.length) {
    throw new Error(`Locale keys do not match. Missing: ${missingKeys.join(', ') || '-'}; extra: ${extraKeys.join(', ') || '-'}`)
  }

  return { zh, trl }
}

function renderLocale(source, locale, filePath = 'template') {
  return source.replace(PLACEHOLDER_PATTERN, (_placeholder, key) => {
    if (!(key in locale)) throw new Error(`Unknown locale key "${key}" in ${filePath}`)
    if (typeof locale[key] !== 'string') throw new Error(`Locale value "${key}" must be a string`)
    return locale[key]
  })
}

function findPlaceholders(source) {
  return Array.from(source.matchAll(PLACEHOLDER_PATTERN), (match) => match[1])
}

function localizeLanguageLinks(source, projectName, filePath, activeLanguage, hrefForLanguage) {
  const device = path.basename(path.dirname(filePath))
  const pageName = path.basename(filePath)

  return source.replace(/<a\b[^>]*data-language="(zh-cn|zh-tw)"[^>]*>/g, (tag, language) => {
    const languageSuffix = language === 'zh-tw' ? 'trl' : 'zh'
    const isActive = languageSuffix === activeLanguage
    const href = hrefForLanguage
      ? hrefForLanguage(languageSuffix, device, pageName)
      : `../../${projectName}_${languageSuffix}/${device}/${pageName}`
    let nextTag = tag
      .replace(/\sdata-href="[^"]*"/g, '')
      .replace(/\saria-current="[^"]*"/g, '')
      .replace(/\sonclick="[^"]*"/g, '')
      .replace(/href="[^"]*"/, `href="${isActive ? '#' : href}"`)
      .replace(/class="([^"]*)"/, (_match, className) => {
        const classes = className.split(/\s+/).filter((name) => name && name !== 'is-active')
        if (isActive) classes.push('is-active')
        return `class="${classes.join(' ')}"`
      })

    const attributes = isActive
      ? ' aria-current="page" onclick="return false;"'
      : ` data-href="${href}" onclick="turnToLanPage(this); return false;"`
    nextTag = nextTag.replace(/>$/, `${attributes}>`)
    return nextTag
  })
}

function renderProjectText(source, options) {
  const { activeLanguage, filePath, hrefForLanguage, locale, projectName } = options
  let rendered = renderLocale(source, locale, filePath)
  if (activeLanguage === 'trl') {
    rendered = rendered.replace(/_zh(?=\/|\\|["'])/g, '_trl')
    rendered = rendered.replace(/\blanguage-zh\b/g, 'language-trl')
  }
  return localizeLanguageLinks(rendered, projectName, filePath, activeLanguage, hrefForLanguage)
}

module.exports = { findPlaceholders, readLocale, readLocales, renderLocale, renderProjectText }
