import { PythonShell } from 'python-shell'
import path from 'path'

export function runPythonScript(
  scriptName: string, 
  data: any, 
  onChunk: (chunk: string) => void
): Promise<void> {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(process.cwd(), 'server', 'scripts', scriptName)
    const pyshell = new PythonShell(scriptPath, { mode: 'text' })

    pyshell.send(JSON.stringify(data))

    pyshell.on('message', (message) => {
      onChunk(message)
    })

    pyshell.end((err) => {
      if (err) {
        reject(err)
      } else {
        resolve()
      }
    })
  })
}