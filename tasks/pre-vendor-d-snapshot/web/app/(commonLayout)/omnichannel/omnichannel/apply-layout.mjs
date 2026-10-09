import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const pagePath = path.join(__dirname, 'page.tsx')
const s = fs.readFileSync(pagePath, 'utf8').replace(/\r\n/g, '\n')
const start = s.indexOf('  return (\n    <div className=\'mx-auto w-full max-w-[1600px] px-6 py-6\'>')
const end = s.search(/\}\r?\n\r?\nexport default OmnichannelPage/)
if (start < 0 || end < 0) {
  console.error('markers', start, end, 'hint: old return wrapper must match exactly')
  process.exit(1)
}
const head = s.slice(0, start)
const tail = s.slice(end)
const mid = [
  fs.readFileSync(path.join(__dirname, '_return-fragment.txt'), 'utf8'),
  fs.readFileSync(path.join(__dirname, '_return-part2.txt'), 'utf8'),
  fs.readFileSync(path.join(__dirname, '_return-part3.txt'), 'utf8'),
].join('\n')
fs.writeFileSync(pagePath, `${head}${mid}\n  )\n${tail}`)
