import { test, expect } from '@playwright/test'
import { AdminPage } from '../../pages/admin/admin.page'
import { createApiClient, ApiClient } from '../../utils/api-client'
import { DataBuilders } from '../../fixtures/data-builders'
import { ADMIN_USER } from '../../config/test-users'

test.describe('Admin - System Config', () => {
  let adminPage: AdminPage
  let apiClient: ApiClient
  let originalConfig: { slogans: unknown[]; tips: unknown[] } | null = null

  test.beforeEach(async ({ page, request }) => {
    adminPage = new AdminPage(page)
    apiClient = createApiClient(request)
    await apiClient.login(ADMIN_USER.username, ADMIN_USER.password)

    const resp = await apiClient.adminGetSloganTipsConfig()
    const data = resp.data as { slogans?: unknown[]; tips?: unknown[] } | null
    originalConfig = {
      slogans: data?.slogans || [],
      tips: data?.tips || [],
    }

    await adminPage.navigateToTab('system-config')
  })

  test.afterEach(async () => {
    if (!originalConfig) return
    await apiClient
      .adminUpdateSloganTipsConfig({
        slogans: originalConfig.slogans,
        tips: originalConfig.tips,
      })
      .catch(() => {})
    originalConfig = null
  })

  test('should add a slogan and save config', async ({ page }) => {
    const sloganZh = `测试 Slogan ${DataBuilders.uniqueId()}`
    const sloganEn = `Test Slogan ${DataBuilders.uniqueId()}`

    await page.locator('button:has-text("Add Slogan"), button:has-text("添加 Slogan")').click()
    await page.locator('[role="dialog"]').waitFor({ state: 'visible' })

    const dialog = page.locator('[role="dialog"]').first()
    await dialog.locator('textarea#item-zh').fill(sloganZh)
    await dialog.locator('textarea#item-en').fill(sloganEn)
    await dialog.locator('button:has-text("Save"), button:has-text("保存")').first().click()

    // Persist to backend
    await page.locator('button:has-text("Save"), button:has-text("保存")').first().click()
    await adminPage.waitForToast().catch(() => {})

    await page.reload()
    await adminPage.waitForPageLoad()
    await expect(page.locator(`text="${sloganZh}"`).first()).toBeVisible({ timeout: 10000 })
  })
})
