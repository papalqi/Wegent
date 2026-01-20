import { test, expect } from '@playwright/test'
import { AdminPage } from '../../pages/admin/admin.page'
import { createApiClient, ApiClient } from '../../utils/api-client'
import { DataBuilders } from '../../fixtures/data-builders'
import { ADMIN_USER } from '../../config/test-users'

test.describe('Admin - API Keys Management', () => {
  let adminPage: AdminPage
  let apiClient: ApiClient
  let serviceKeyName = ''
  let personalKeyId: number | null = null
  let personalKeyName = ''

  test.beforeEach(async ({ page, request }) => {
    adminPage = new AdminPage(page)
    apiClient = createApiClient(request)
    await apiClient.login(ADMIN_USER.username, ADMIN_USER.password)

    await adminPage.navigateToTab('api-keys')
  })

  test.afterEach(async () => {
    if (serviceKeyName) {
      const listResponse = await apiClient.adminListServiceKeys().catch(() => null)
      const items =
        (listResponse?.data as { items?: Array<{ id: number; name: string }> } | null)?.items || []
      const match = items.find(k => k.name === serviceKeyName)
      if (match) {
        await apiClient.adminDeleteServiceKey(match.id).catch(() => {})
      }
      serviceKeyName = ''
    }

    if (personalKeyId) {
      await apiClient.adminDeletePersonalKey(personalKeyId).catch(() => {})
      personalKeyId = null
      personalKeyName = ''
    }
  })

  test('should create, toggle, and delete a service key', async ({ page }) => {
    serviceKeyName = DataBuilders.uniqueName('e2e-service-key')

    await page
      .locator('button:has-text("Create Service Key"), button:has-text("创建服务密钥")')
      .first()
      .click()

    const createDialog = page.locator('[role="dialog"]').first()
    await createDialog.waitFor({ state: 'visible' })

    await createDialog
      .locator('input[placeholder*="Enter key name"], input[placeholder*="请输入密钥名称"]')
      .first()
      .fill(serviceKeyName)

    await createDialog
      .locator(
        'textarea[placeholder*="Enter key description"], textarea[placeholder*="请输入密钥描述"]'
      )
      .first()
      .fill('E2E service key')

    await createDialog.locator('button:has-text("Create"), button:has-text("创建")').first().click()

    await adminPage.waitForToast().catch(() => {})

    // Created key is shown once
    const createdDialog = page.locator('[role="dialog"]').first()
    await createdDialog.waitFor({ state: 'visible' })
    await expect(createdDialog.locator('code').first()).toContainText('wg-')
    await createdDialog.locator('button:has-text("Close"), button:has-text("关闭")').first().click()

    await expect(page.locator(`text="${serviceKeyName}"`).first()).toBeVisible({ timeout: 10000 })

    // Toggle status
    const card = page.locator(`div:has-text("${serviceKeyName}")`).first()
    await card.locator('[role="switch"]').first().click()
    await adminPage.waitForToast().catch(() => {})

    // Delete
    await card.locator('button[title*="Delete"], button[title*="删除"]').first().click()
    await page.locator('[role="alertdialog"]').waitFor({ state: 'visible' })
    await page
      .locator(
        '[role="alertdialog"] button:has-text("Delete"), [role="alertdialog"] button:has-text("删除")'
      )
      .first()
      .click()

    await adminPage.waitForToast().catch(() => {})
    await expect(page.locator(`text="${serviceKeyName}"`).first()).toBeHidden({ timeout: 10000 })
    serviceKeyName = ''
  })

  test('should list, toggle, and delete personal keys', async ({ page }) => {
    personalKeyName = DataBuilders.uniqueName('e2e-personal-key')
    const createResponse = await apiClient.createPersonalApiKey({
      name: personalKeyName,
      description: 'E2E personal key',
    })

    personalKeyId = (createResponse.data as { id?: number } | null)?.id || null
    expect(personalKeyId).not.toBeNull()

    await page.locator('button:has-text("Personal Keys"), button:has-text("个人密钥")').click()

    const searchInput = page
      .locator(
        'input[placeholder*="Search username or key name"], input[placeholder*="搜索用户名或密钥名称"]'
      )
      .first()
    await searchInput.fill(personalKeyName)

    await expect(page.locator(`text="${personalKeyName}"`).first()).toBeVisible({ timeout: 10000 })

    const keyCard = page.locator(`div:has-text("${personalKeyName}")`).first()

    await keyCard.locator('[role="switch"]').first().click()
    await adminPage.waitForToast().catch(() => {})

    await keyCard.locator('button[title*="Delete"], button[title*="删除"]').first().click()
    await page.locator('[role="alertdialog"]').waitFor({ state: 'visible' })
    await page
      .locator(
        '[role="alertdialog"] button:has-text("Delete"), [role="alertdialog"] button:has-text("删除")'
      )
      .first()
      .click()

    await adminPage.waitForToast().catch(() => {})
    await expect(page.locator(`text="${personalKeyName}"`).first()).toBeHidden({ timeout: 10000 })

    personalKeyId = null
    personalKeyName = ''
  })
})
