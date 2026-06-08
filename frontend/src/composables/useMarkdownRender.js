/**
 * Markdown 渲染引擎封装
 * 基于 marked，整合 doocs/md 的渲染模式和主题系统
 */
import { marked } from 'marked'
import hljs from 'highlight.js'

// 配置 marked
marked.setOptions({
  breaks: true,
  gfm: true,
})

// 配置 highlight.js
const highlightCode = (code, lang) => {
  if (lang && hljs.getLanguage(lang)) {
    try {
      return hljs.highlight(code, { language: lang }).value
    } catch (e) { /* fall through */ }
  }
  return code
}

// 自定义渲染器
const renderer = new marked.Renderer()

// 代码块渲染
renderer.code = function ({ text, lang }) {
  const highlighted = highlightCode(text, lang)
  const langLabel = lang ? `<span class="code-lang">${lang}</span>` : ''
  return `<pre class="hljs"><code class="language-${lang || ''}">${highlighted}</code>${langLabel}</pre>`
}

// 图片渲染 - 支持尺寸标记 |WxH
renderer.image = function ({ href, title, text }) {
  let widthAttr = ''
  let heightAttr = ''
  let altText = text || ''
  const sizeMatch = altText.match(/\|(\d+)(?:x(\d+))?$/)
  if (sizeMatch) {
    altText = altText.replace(/\|(\d+)(?:x(\d+))?$/, '')
    widthAttr = sizeMatch[1] ? ` width="${sizeMatch[1]}"` : ''
    heightAttr = sizeMatch[2] ? ` height="${sizeMatch[2]}"` : ''
  }
  const titleAttr = title ? ` title="${title}"` : ''
  const figcaption = altText ? `<figcaption>${altText}</figcaption>` : ''
  return `<figure><img src="${href}"${titleAttr}${widthAttr}${heightAttr} alt="${altText}"/>${figcaption}</figure>`
}

// 链接渲染 - 微信链接特殊处理
renderer.link = function ({ href, title, text }) {
  const titleAttr = title ? ` title="${title}"` : ''
  return `<a href="${href}"${titleAttr}>${text}</a>`
}

// 表格渲染 - 添加滚动容器
renderer.table = function ({ header, rows }) {
  const headerHtml = `<thead><tr>${header.map(cell => `<th>${cell.text}</th>`).join('')}</tr></thead>`
  const bodyHtml = `<tbody>${rows.map(row => `<tr>${row.map(cell => `<td>${cell.text}</td>`).join('')}</tr>`).join('')}</tbody>`
  return `<div class="table-wrapper"><table>${headerHtml}${bodyHtml}</table></div>`
}

marked.use({ renderer })

/**
 * 渲染 Markdown 为 HTML
 * @param {string} markdown - Markdown 文本
 * @returns {string} HTML 字符串
 */
export function renderMarkdown(markdown) {
  if (!markdown) return ''
  return marked.parse(markdown)
}

/**
 * 获取指定主题的完整 CSS（base + theme）
 * @param {string} themeName - 主题名称: 'default' | 'grace' | 'simple'
 * @returns {Promise<string>} 合并后的 CSS
 */
export async function getThemeCSS(themeName = 'default') {
  const modules = {
    base: () => import('../assets/themes/md-base.css?raw'),
    default: () => import('../assets/themes/md-default.css?raw'),
    grace: () => import('../assets/themes/md-grace.css?raw'),
    simple: () => import('../assets/themes/md-simple.css?raw'),
  }

  const base = await modules.base()
  const theme = modules[themeName] ? await modules[themeName]() : await modules.default()
  return `${base.default}\n${theme.default}`
}

/**
 * HTML 转义
 * @param {string} html - 原始 HTML
 * @returns {string} 转义后的文本
 */
export function escapeHtml(html) {
  return String(html)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

/**
 * HTML 转 Markdown（简单转换）
 * @param {string} html - HTML 内容
 * @returns {string} Markdown 文本
 */
export function htmlToMarkdown(html) {
  if (!html) return ''
  let md = html
  // 移除 HTML 标签，保留文本
  md = md.replace(/<h1[^>]*>(.*?)<\/h1>/gi, '# $1\n\n')
  md = md.replace(/<h2[^>]*>(.*?)<\/h2>/gi, '## $1\n\n')
  md = md.replace(/<h3[^>]*>(.*?)<\/h3>/gi, '### $1\n\n')
  md = md.replace(/<h4[^>]*>(.*?)<\/h4>/gi, '#### $1\n\n')
  md = md.replace(/<strong[^>]*>(.*?)<\/strong>/gi, '**$1**')
  md = md.replace(/<b[^>]*>(.*?)<\/b>/gi, '**$1**')
  md = md.replace(/<em[^>]*>(.*?)<\/em>/gi, '*$1*')
  md = md.replace(/<i[^>]*>(.*?)<\/i>/gi, '*$1*')
  md = md.replace(/<p[^>]*>(.*?)<\/p>/gi, '$1\n\n')
  md = md.replace(/<br\s*\/?>/gi, '\n')
  md = md.replace(/<a[^>]*href="(.*?)"[^>]*>(.*?)<\/a>/gi, '[$2]($1)')
  md = md.replace(/<img[^>]*src="(.*?)"[^>]*alt="(.*?)"[^>]*>/gi, '![$2]($1)')
  md = md.replace(/<figure[^>]*>.*?<\/figure>/gi, '')
  md = md.replace(/<[^>]+>/g, '')
  md = md.replace(/&amp;/g, '&')
  md = md.replace(/&lt;/g, '<')
  md = md.replace(/&gt;/g, '>')
  md = md.replace(/&quot;/g, '"')
  md = md.replace(/&nbsp;/g, ' ')
  return md.trim()
}
