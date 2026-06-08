/**
 * Markdown 一键格式化封装
 * 使用 Prettier standalone 格式化 Markdown 内容
 */
import * as prettier from 'prettier/standalone'
// @ts-ignore
import parserMarkdown from 'prettier/plugins/markdown'
// @ts-ignore
import parserBabel from 'prettier/plugins/babel'

/**
 * 格式化 Markdown 文档
 * @param {string} content - Markdown 内容
 * @returns {Promise<string>} 格式化后的内容
 */
export async function formatMarkdown(content) {
  if (!content) return ''
  try {
    return await prettier.format(content, {
      parser: 'markdown',
      plugins: [parserMarkdown, parserBabel],
      printWidth: 80,
      tabWidth: 2,
      useTabs: false,
      semi: false,
      singleQuote: true,
      proseWrap: 'preserve',
    })
  } catch (e) {
    console.warn('Markdown formatting failed:', e)
    return content
  }
}

/**
 * 格式化 CSS 内容
 * @param {string} content - CSS 内容
 * @returns {Promise<string>} 格式化后的内容
 */
export async function formatCSS(content) {
  if (!content) return ''
  try {
    // @ts-ignore
    const parserPostcss = await import('prettier/plugins/postcss')
    return await prettier.format(content, {
      parser: 'css',
      plugins: [parserPostcss.default],
      printWidth: 80,
      tabWidth: 2,
    })
  } catch (e) {
    console.warn('CSS formatting failed:', e)
    return content
  }
}
