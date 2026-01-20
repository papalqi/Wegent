import { execFileSync } from 'child_process'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'

export function createTempSkillZip(options: { skillName: string; skillMdContent: string }): {
  zipPath: string
  tempDir: string
} {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'wegent-skill-'))

  const skillRoot = path.join(tempDir, options.skillName)
  fs.mkdirSync(skillRoot, { recursive: true })
  fs.mkdirSync(path.join(skillRoot, 'resources'), { recursive: true })

  fs.writeFileSync(path.join(skillRoot, 'SKILL.md'), options.skillMdContent, 'utf8')
  fs.writeFileSync(path.join(skillRoot, 'resources', 'hello.txt'), 'hello', 'utf8')

  const zipPath = path.join(tempDir, `${options.skillName}.zip`)

  const pythonScript = `
import os
import zipfile

zip_path = os.environ["ZIP_PATH"]
root_dir = os.environ["ROOT_DIR"]
skill_name = os.environ["SKILL_NAME"]
skill_dir = os.path.join(root_dir, skill_name)

with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for folder, _, files in os.walk(skill_dir):
        for filename in files:
            abs_path = os.path.join(folder, filename)
            rel_path = os.path.relpath(abs_path, root_dir)
            zf.write(abs_path, rel_path)
`

  execFileSync('python3', ['-c', pythonScript], {
    env: {
      ...process.env,
      ZIP_PATH: zipPath,
      ROOT_DIR: tempDir,
      SKILL_NAME: options.skillName,
    },
    stdio: 'ignore',
  })

  return { zipPath, tempDir }
}
