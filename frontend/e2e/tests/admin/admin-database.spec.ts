import { test, expect } from '@playwright/test'
import { AdminPage } from '../../pages/admin/admin.page'
import { createApiClient, ApiClient } from '../../utils/api-client'
import { ADMIN_USER } from '../../config/test-users'
import * as fs from 'fs'
import * as os from 'os'
import * as path from 'path'

test.describe('Admin - Database Management', () => {
  let adminPage: AdminPage
  let apiClient: ApiClient
  const tempDirs: string[] = []

  test.beforeEach(async ({ page, request }) => {
    adminPage = new AdminPage(page)
    apiClient = createApiClient(request)
    await apiClient.login(ADMIN_USER.username, ADMIN_USER.password)

    await adminPage.navigateToTab('database')
  })

  test.afterEach(async () => {
    for (const dir of tempDirs) {
      fs.rmSync(dir, { recursive: true, force: true })
    }
    tempDirs.length = 0
  })

  test('should export database (request succeeds)', async ({ page }) => {
    const exportResponsePromise = page.waitForResponse(
      resp => resp.url().includes('/api/admin/database/export') && resp.status() === 200
    )

    await page.locator('button:has-text("Export Database"), button:has-text("导出数据库")').click()

    await exportResponsePromise
    await adminPage.waitForToast().catch(() => {})
  })

  test('should show import warning and allow cancel', async ({ page }) => {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wegent-db-'))
    tempDirs.push(dir)
    const sqlPath = path.join(dir, 'e2e.sql')
    fs.writeFileSync(sqlPath, 'CREATE TABLE IF NOT EXISTS e2e_test (id INT);\n', 'utf8')

    await page.setInputFiles('input#database-import-file', sqlPath)

    await page.locator('[role="alertdialog"]').waitFor({ state: 'visible' })
    await page
      .locator(
        '[role="alertdialog"] button:has-text("Cancel"), [role="alertdialog"] button:has-text("取消")'
      )
      .first()
      .click()

    await expect(page.locator('[role="alertdialog"]').first()).toBeHidden({ timeout: 10000 })
  })
})
