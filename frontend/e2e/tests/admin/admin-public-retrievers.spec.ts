import { test, expect } from '@playwright/test'
import { AdminPage } from '../../pages/admin/admin.page'
import { createApiClient, ApiClient } from '../../utils/api-client'
import { DataBuilders } from '../../fixtures/data-builders'
import { ADMIN_USER } from '../../config/test-users'

test.describe('Admin - Public Retriever Management', () => {
  let adminPage: AdminPage
  let apiClient: ApiClient
  let retrieverName = ''

  test.beforeEach(async ({ page, request }) => {
    adminPage = new AdminPage(page)
    apiClient = createApiClient(request)
    await apiClient.login(ADMIN_USER.username, ADMIN_USER.password)

    await adminPage.navigateToTab('public-retrievers')
  })

  test.afterEach(async () => {
    if (!retrieverName) return

    const listResponse = await apiClient.adminListPublicRetrievers(1, 200).catch(() => null)
    const items = (listResponse?.data as { items?: Array<{ id: number; name: string }> } | null)
      ?.items
    const match = items?.find(r => r.name === retrieverName)
    if (match) {
      await apiClient.adminDeletePublicRetriever(match.id).catch(() => {})
    }
    retrieverName = ''
  })

  test('should access public retrievers tab', async ({ page }) => {
    expect(adminPage.isOnAdminPage()).toBe(true)
    await expect(
      page.locator('button:has-text("Create Retriever"), button:has-text("创建检索引擎")').first()
    ).toBeVisible({ timeout: 10000 })
  })

  test('should create, edit, and delete a public retriever', async ({ page }) => {
    retrieverName = DataBuilders.uniqueName('e2e-retriever')
    const displayName = `E2E Retriever ${DataBuilders.uniqueId()}`

    await page
      .locator('button:has-text("Create Retriever"), button:has-text("创建检索引擎")')
      .first()
      .click()

    await page.locator('[role="dialog"]').waitFor({ state: 'visible' })

    const dialog = page.locator('[role="dialog"]').first()
    await dialog.locator('input#name').fill(retrieverName)
    await dialog.locator('input#displayName').fill(displayName)
    await dialog.locator('input#url').fill('http://elasticsearch:9200')

    await dialog.locator('button:has-text("Create"), button:has-text("创建")').first().click()

    await adminPage.waitForToast().catch(() => {})

    await expect(page.locator(`text="${retrieverName}"`).first()).toBeVisible({ timeout: 10000 })

    // Edit
    const updatedDisplayName = `${displayName} Updated`
    const card = page.locator(`div:has-text("${retrieverName}")`).first()
    await card.locator('button[title*="Edit"], button[title*="编辑"]').first().click()
    await page.locator('[role="dialog"]').waitFor({ state: 'visible' })

    const editDialog = page.locator('[role="dialog"]').first()
    await editDialog.locator('input#displayName').fill(updatedDisplayName)
    await editDialog.locator('button:has-text("Save"), button:has-text("保存")').first().click()
    await adminPage.waitForToast().catch(() => {})

    await expect(page.locator(`text="${updatedDisplayName}"`).first()).toBeVisible({
      timeout: 10000,
    })

    // Delete
    const updatedCard = page.locator(`div:has-text("${updatedDisplayName}")`).first()
    await updatedCard.locator('button[title*="Delete"], button[title*="删除"]').first().click()
    await page.locator('[role="alertdialog"]').waitFor({ state: 'visible' })

    await page
      .locator(
        '[role="alertdialog"] button:has-text("Delete"), [role="alertdialog"] button:has-text("删除")'
      )
      .first()
      .click()

    await adminPage.waitForToast().catch(() => {})
    await expect(page.locator(`text="${retrieverName}"`).first()).toBeHidden({ timeout: 10000 })

    retrieverName = ''
  })
})
