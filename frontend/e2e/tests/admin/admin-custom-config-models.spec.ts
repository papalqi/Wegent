import { test, expect } from '@playwright/test'
import { AdminPage } from '../../pages/admin/admin.page'
import { createApiClient, ApiClient } from '../../utils/api-client'
import { DataBuilders } from '../../fixtures/data-builders'
import { ADMIN_USER } from '../../config/test-users'

test.describe('Admin - Custom Config Models', () => {
  let adminPage: AdminPage
  let apiClient: ApiClient
  let modelName = ''

  test.beforeEach(async ({ page, request }) => {
    adminPage = new AdminPage(page)
    apiClient = createApiClient(request)
    await apiClient.login(ADMIN_USER.username, ADMIN_USER.password)
  })

  test.afterEach(async () => {
    if (!modelName) return

    const listResp = await apiClient
      .adminListCustomConfigModels(1, 200, true, modelName)
      .catch(() => null)
    const items =
      (listResp?.data as { items?: Array<{ id: number; name: string }> } | null)?.items || []
    const match = items.find(m => m.name === modelName)
    if (match) {
      await apiClient.adminDeleteCustomConfigModel(match.id, true).catch(() => {})
    }
    modelName = ''
  })

  test('should list and delete a custom-config model', async ({ page }) => {
    modelName = DataBuilders.uniqueName('e2e-custom-config-model')

    await apiClient.createModelResource('default', {
      apiVersion: 'agent.wecode.io/v1',
      kind: 'Model',
      metadata: {
        name: modelName,
        namespace: 'default',
      },
      spec: {
        isCustomConfig: true,
        protocol: 'openai',
        modelConfig: {
          env: {
            model: 'openai',
            model_id: 'gpt-4o-mini',
            base_url: 'https://example.invalid/v1',
            api_key: '${E2E_FAKE_KEY}',
          },
        },
      },
      status: { state: 'Available' },
    })

    await adminPage.navigateToTab('custom-config-models')

    const searchInput = page
      .locator('input[placeholder*="Search model/user"], input[placeholder*="搜索模型"]')
      .first()
    await searchInput.fill(modelName)
    await page.locator('button:has-text("Search"), button:has-text("搜索")').first().click()

    await expect(page.locator(`text="${modelName}"`).first()).toBeVisible({ timeout: 10000 })

    // Open cleanup preview dialog and cancel (no side effects)
    await page
      .locator('button:has-text("Cleanup orphans"), button:has-text("清理孤儿模型")')
      .first()
      .click()
    await page.locator('[role="alertdialog"]').waitFor({ state: 'visible' })
    await page
      .locator(
        '[role="alertdialog"] button:has-text("Cancel"), [role="alertdialog"] button:has-text("取消")'
      )
      .first()
      .click()

    // Delete via UI
    const card = page.locator(`div:has-text("${modelName}")`).first()
    await card.locator('button[title*="Delete"], button[title*="删除"]').first().click()

    await page.locator('[role="alertdialog"]').waitFor({ state: 'visible' })
    await page
      .locator(
        '[role="alertdialog"] button:has-text("Delete"), [role="alertdialog"] button:has-text("删除")'
      )
      .first()
      .click()

    await adminPage.waitForToast().catch(() => {})
    await expect(page.locator(`text="${modelName}"`).first()).toBeHidden({ timeout: 10000 })
    modelName = ''
  })
})
